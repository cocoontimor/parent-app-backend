"""Tests for the payments data migrations."""
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MergeDuplicateMonthsMigrationTests(TransactionTestCase):
    before = [("payments", "0001_initial"), ("children", "0005_child_graduation_date")]
    after = [("payments", "0002_feepayment_marked_by_feepayment_paid_at_and_more")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        apps = executor.loader.project_state(self.before).apps
        Child = apps.get_model("children", "Child")
        FeePayment = apps.get_model("payments", "FeePayment")
        ann = Child.objects.create(name="Ann")
        bob = Child.objects.create(name="Bob")
        FeePayment.objects.create(child=ann, month="2026-08", amount=30)
        FeePayment.objects.create(child=ann, month="2026-08", amount=20)
        FeePayment.objects.create(child=ann, month="2026-09", amount=50)
        FeePayment.objects.create(child=bob, month="2026-08", amount=50)

    def tearDown(self):
        MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        )

    def test_duplicates_fold_into_one_row_with_summed_amount(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        apps = executor.loader.project_state(self.after).apps
        FeePayment = apps.get_model("payments", "FeePayment")
        rows = sorted(
            (p.child.name, p.month, p.amount) for p in FeePayment.objects.all()
        )
        self.assertEqual(
            rows,
            [
                ("Ann", "2026-08", Decimal("50.00")),
                ("Ann", "2026-09", Decimal("50.00")),
                ("Bob", "2026-08", Decimal("50.00")),
            ],
        )
