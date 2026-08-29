import logging

logger = logging.getLogger(__name__)


def _recipient_parents(child):
    """Parents to notify for a child: users who are members of the child's
    family circle(s) with a parent relationship."""
    from django.contrib.auth import get_user_model

    from children.models import Circle, Member

    User = get_user_model()
    parent_relationships = (
        Member.Relationship.MOTHER,
        Member.Relationship.FATHER,
        Member.Relationship.GUARDIAN,
    )
    family_circles = child.circles.filter(type=Circle.Type.FAMILY)
    return User.objects.filter(
        memberships__circle__in=family_circles,
        memberships__relationship__in=parent_relationships,
    ).distinct()


def send_payment_confirmation(payment):
    """Send a WhatsApp confirmation of a logged fee payment to every parent in
    the child's family circle(s). Reuses the messaging pipeline."""
    from messaging.services import send_whatsapp_message

    child = payment.child
    body = (
        f"Payment of {payment.amount} recorded for {child.name}, "
        f"covering {payment.month}."
    )

    recipients = _recipient_parents(child)
    for user in recipients:
        send_whatsapp_message(
            user,
            template="payment_confirmation",
            body=body,
            variables=[str(payment.amount), child.name, payment.month],
        )

    count = recipients.count()
    logger.info(
        "Sent payment confirmation for payment %s to %d parent(s)",
        payment.id,
        count,
    )
    return count
