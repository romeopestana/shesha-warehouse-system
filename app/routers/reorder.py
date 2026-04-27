from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import InventoryLot, Product, ReorderProposal, ReorderProposalItem, StockMovement
from app.notifications import emit_notification
from app.schemas import (
    ReorderApprovalAppliedItem,
    ReorderApprovalBlockedItem,
    ReorderProposalApprovalResult,
    ReorderProposalOut,
    ReorderProposalRejectRequest,
    SuggestedReorderCreate,
    SuggestedReorderCreatedItem,
    SuggestedReorderResult,
    SuggestedReorderSkippedItem,
)

router = APIRouter(prefix="/reorders", tags=["reorders"])


@router.post("/suggested", response_model=SuggestedReorderResult)
def create_suggested_reorders(
    payload: SuggestedReorderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    query = db.query(Product).filter(Product.quantity_on_hand <= Product.reorder_level)

    if payload.warehouse_id is not None:
        query = query.filter(Product.warehouse_id == payload.warehouse_id)
    if payload.product_ids:
        query = query.filter(Product.id.in_(payload.product_ids))

    products = query.order_by(Product.id.asc()).all()
    proposal = ReorderProposal(
        status="pending",
        note=payload.note,
        created_by=current_user.username,
    )
    db.add(proposal)
    db.flush()
    emit_notification(
        db=db,
        event_type="reorder_proposal_submitted",
        message=f"Reorder proposal #{proposal.id} submitted by {current_user.username}",
        related_id=proposal.id,
    )

    created: list[SuggestedReorderCreatedItem] = []
    skipped: list[SuggestedReorderSkippedItem] = []

    for product in products:
        if product.reorder_quantity <= 0:
            skipped.append(
                SuggestedReorderSkippedItem(
                    product_id=product.id,
                    reason="reorder_quantity is 0",
                )
            )
            continue

        before = product.quantity_on_hand
        after = product.quantity_on_hand + product.reorder_quantity
        if not payload.dry_run:
            product.quantity_on_hand = after
            db.add(
                InventoryLot(
                    product_id=product.id,
                    quantity_remaining=product.reorder_quantity,
                )
            )
            db.add(
                StockMovement(
                    product_id=product.id,
                    movement_type="IN",
                    quantity=product.reorder_quantity,
                    note=payload.note,
                    performed_by=current_user.username,
                )
            )
            db.add(product)

        proposal_item = ReorderProposalItem(
            proposal_id=proposal.id,
            product_id=product.id,
            warehouse_id=product.warehouse_id,
            quantity_before=before,
            quantity_added=product.reorder_quantity,
            quantity_after=after,
        )
        db.add(proposal_item)
        created.append(
            SuggestedReorderCreatedItem(
                product_id=product.id,
                quantity_added=product.reorder_quantity,
                quantity_before=before,
                quantity_after=after,
                warehouse_id=product.warehouse_id,
            )
        )

    if payload.dry_run:
        db.commit()
        return SuggestedReorderResult(proposal_id=proposal.id, created=created, skipped=skipped)

    # Non-dry runs execute immediately and auto-approve the generated proposal.
    proposal.status = "approved"
    proposal.reviewed_by = current_user.username
    proposal.reviewed_at = datetime.utcnow()
    db.add(proposal)
    emit_notification(
        db=db,
        event_type="reorder_proposal_approved",
        message=f"Reorder proposal #{proposal.id} auto-approved",
        related_id=proposal.id,
    )
    db.commit()
    return SuggestedReorderResult(proposal_id=proposal.id, created=created, skipped=skipped)


@router.get("/proposals", response_model=list[ReorderProposalOut])
def list_reorder_proposals(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
    status: str | None = Query(default=None),
):
    query = db.query(ReorderProposal)
    if status is not None:
        query = query.filter(ReorderProposal.status == status)
    return query.order_by(ReorderProposal.id.desc()).all()


@router.post("/proposals/{proposal_id}/approve", response_model=ReorderProposalApprovalResult)
def approve_reorder_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
    force: bool = Query(default=False),
):
    proposal = db.query(ReorderProposal).filter(ReorderProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail="Proposal is not pending")

    items = (
        db.query(ReorderProposalItem)
        .filter(ReorderProposalItem.proposal_id == proposal.id)
        .order_by(ReorderProposalItem.id.asc())
        .all()
    )
    applied: list[ReorderApprovalAppliedItem] = []
    blocked: list[ReorderApprovalBlockedItem] = []

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            blocked.append(
                ReorderApprovalBlockedItem(
                    item_id=item.id,
                    product_id=item.product_id,
                    reason="product no longer exists",
                )
            )
            continue
        if product.warehouse_id != item.warehouse_id:
            blocked.append(
                ReorderApprovalBlockedItem(
                    item_id=item.id,
                    product_id=item.product_id,
                    reason="product warehouse changed since proposal",
                )
            )
            continue
        if not force and product.quantity_on_hand > product.reorder_level:
            blocked.append(
                ReorderApprovalBlockedItem(
                    item_id=item.id,
                    product_id=item.product_id,
                    reason="product is no longer low-stock",
                )
            )
            continue

        product.quantity_on_hand += item.quantity_added
        db.add(
            InventoryLot(
                product_id=product.id,
                quantity_remaining=item.quantity_added,
            )
        )
        db.add(
            StockMovement(
                product_id=product.id,
                movement_type="IN",
                quantity=item.quantity_added,
                note=f"APPROVED_REORDER_PROPOSAL:{proposal.id} {proposal.note}".strip(),
                performed_by=current_user.username,
            )
        )
        db.add(product)
        applied.append(
            ReorderApprovalAppliedItem(
                item_id=item.id,
                product_id=item.product_id,
                quantity_added=item.quantity_added,
            )
        )

    if not applied and blocked:
        raise HTTPException(
            status_code=400,
            detail="No proposal items can be approved due to drift; use force=true to override stock-level drift only.",
        )

    proposal.status = "approved"
    proposal.reviewed_by = current_user.username
    proposal.reviewed_at = datetime.utcnow()
    db.add(proposal)
    emit_notification(
        db=db,
        event_type="reorder_proposal_approved",
        message=f"Reorder proposal #{proposal.id} approved by {current_user.username}",
        related_id=proposal.id,
    )
    db.commit()
    db.refresh(proposal)
    return ReorderProposalApprovalResult(proposal=proposal, applied=applied, blocked=blocked)


@router.post("/proposals/{proposal_id}/reject", response_model=ReorderProposalOut)
def reject_reorder_proposal(
    proposal_id: int,
    payload: ReorderProposalRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    proposal = db.query(ReorderProposal).filter(ReorderProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(status_code=400, detail="Proposal is not pending")

    proposal.status = "rejected"
    proposal.reviewed_by = current_user.username
    proposal.reviewed_at = datetime.utcnow()
    proposal.rejection_reason = payload.reason
    db.add(proposal)
    emit_notification(
        db=db,
        event_type="reorder_proposal_rejected",
        message=f"Reorder proposal #{proposal.id} rejected by {current_user.username}",
        related_id=proposal.id,
    )
    db.commit()
    db.refresh(proposal)
    return proposal
