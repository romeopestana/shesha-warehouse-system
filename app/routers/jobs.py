from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import JobRun, Product, ReorderProposal, ReorderProposalItem
from app.notifications import emit_notification
from app.schemas import DailyReorderScanOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/daily-reorder-scan", response_model=DailyReorderScanOut)
def run_daily_reorder_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    run_date = datetime.now(timezone.utc).date().isoformat()
    low_stock_products = (
        db.query(Product)
        .filter(
            Product.quantity_on_hand <= Product.reorder_level,
            Product.reorder_quantity > 0,
        )
        .order_by(Product.warehouse_id.asc(), Product.id.asc())
        .all()
    )

    by_warehouse: dict[int, list[Product]] = {}
    for product in low_stock_products:
        by_warehouse.setdefault(product.warehouse_id, []).append(product)

    proposal_ids: list[int] = []
    pending_ids: list[int] = []
    skipped_existing_runs = 0

    for warehouse_id, products in by_warehouse.items():
        existing = (
            db.query(JobRun)
            .filter(
                JobRun.job_name == "daily_reorder_scan",
                JobRun.run_date == run_date,
                JobRun.warehouse_id == warehouse_id,
            )
            .first()
        )
        if existing:
            skipped_existing_runs += 1
            continue

        proposal = ReorderProposal(
            status="pending",
            note=f"Daily scan proposal ({run_date})",
            created_by=current_user.username,
        )
        db.add(proposal)
        db.flush()

        for product in products:
            before = product.quantity_on_hand
            added = product.reorder_quantity
            db.add(
                ReorderProposalItem(
                    proposal_id=proposal.id,
                    product_id=product.id,
                    warehouse_id=product.warehouse_id,
                    quantity_before=before,
                    quantity_added=added,
                    quantity_after=before + added,
                )
            )

        pending_ids.append(proposal.id)
        emit_notification(
            db=db,
            event_type="daily_scan_requires_manual_approval",
            message=f"Daily scan proposal #{proposal.id} requires manual approval",
            related_id=proposal.id,
        )

        db.add(
            JobRun(
                job_name="daily_reorder_scan",
                run_date=run_date,
                warehouse_id=warehouse_id,
                status="completed",
                details=f"proposal_id={proposal.id}",
            )
        )
        emit_notification(
            db=db,
            event_type="daily_reorder_scan_created",
            message=f"Daily reorder proposal #{proposal.id} created for warehouse {warehouse_id}",
            related_id=proposal.id,
        )
        proposal_ids.append(proposal.id)

    emit_notification(
        db=db,
        event_type="daily_reorder_scan_summary",
        message=(
            f"Daily reorder scan {run_date}: created={len(proposal_ids)}, "
            f"skipped_existing={skipped_existing_runs}"
        ),
        related_id=None,
    )
    db.commit()

    return DailyReorderScanOut(
        run_date=run_date,
        warehouses_scanned=len(by_warehouse),
        proposals_created=len(proposal_ids),
        skipped_existing_runs=skipped_existing_runs,
        proposal_ids=proposal_ids,
        pending_ids=pending_ids,
    )
