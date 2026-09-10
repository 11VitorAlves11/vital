import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import Biomarker, BiomarkerMatchRule
from app.schemas.match_rules import BiomarkerMatchRuleOut

router = APIRouter(prefix="/biomarker-match-rules", tags=["biomarker match rules"])


@router.get("", response_model=list[BiomarkerMatchRuleOut])
async def list_match_rules(user: CurrentUser, db: DbSession) -> list[BiomarkerMatchRuleOut]:
    rows = (
        await db.execute(
            select(BiomarkerMatchRule, Biomarker)
            .join(Biomarker, Biomarker.id == BiomarkerMatchRule.biomarker_id)
            .where(BiomarkerMatchRule.user_id == user.id)
            .order_by(
                BiomarkerMatchRule.lab_name,
                BiomarkerMatchRule.source_name,
                BiomarkerMatchRule.source_unit,
            )
        )
    ).all()
    return [
        BiomarkerMatchRuleOut(
            id=rule.id,
            lab_name=rule.lab_name,
            source_name=rule.source_name,
            source_unit=rule.source_unit,
            biomarker_id=biomarker.id,
            biomarker_name=biomarker.name,
            biomarker_unit=biomarker.canonical_unit,
            created_at=rule.created_at,
        )
        for rule, biomarker in rows
    ]


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match_rule(
    rule_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> Response:
    rule = await db.scalar(
        select(BiomarkerMatchRule).where(
            BiomarkerMatchRule.id == rule_id, BiomarkerMatchRule.user_id == user.id
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match rule not found")
    await db.delete(rule)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
