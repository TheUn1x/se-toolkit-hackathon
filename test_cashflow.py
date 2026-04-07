"""
Comprehensive tests for CashFlow API
Covers: groups, expenses with split types, balances, settlements, edge cases, optimization
"""
import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cashflow_api import CashFlowAPI, round_money, distribute_remainder


class TestRoundMoney(unittest.TestCase):
    """Test rounding utility"""

    def test_basic_rounding(self):
        self.assertEqual(round_money(10.123), 10.12)
        self.assertEqual(round_money(10.125), 10.13)
        self.assertEqual(round_money(10.127), 10.13)

    def test_negative(self):
        # ROUND_HALF_UP: -10.125 rounds to -10.13 (away from zero for .5)
        self.assertEqual(round_money(-10.125), -10.13)

    def test_already_rounded(self):
        self.assertEqual(round_money(10.10), 10.1)


class TestDistributeRemainder(unittest.TestCase):
    """Test remainder distribution"""

    def test_equal_split_no_remainder(self):
        result = distribute_remainder(300.0, [100.0, 100.0, 100.0])
        self.assertEqual(result, [100.0, 100.0, 100.0])
        self.assertAlmostEqual(sum(result), 300.0)

    def test_equal_split_with_remainder(self):
        result = distribute_remainder(100.0, [33.333, 33.333, 33.333])
        self.assertAlmostEqual(sum(result), 100.0)
        # One should get an extra kopeck
        self.assertTrue(any(abs(r - 33.34) < 0.001 for r in result))

    def test_two_way_split(self):
        result = distribute_remainder(100.0, [50.0, 50.0])
        self.assertEqual(result, [50.0, 50.0])


class TestCashFlowAPI(unittest.TestCase):
    """Main test suite for CashFlowAPI"""

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_file.close()
        self.cf = CashFlowAPI(self.temp_file.name)
        self._create_test_users()

    def tearDown(self):
        try:
            os.unlink(self.temp_file.name)
        except OSError:
            pass

    def _create_test_users(self):
        self.user1 = self.cf.register_user(1, "Alice", "alice")
        self.user2 = self.cf.register_user(2, "Bob", "bob")
        self.user3 = self.cf.register_user(3, "Charlie", "charlie")
        self.user4 = self.cf.register_user(4, "Diana", "diana")

    # ==================== BASIC EXPENSE TESTS ====================

    def test_basic_expense_two_people(self):
        """Alice pays 300 for dinner split with Bob"""
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=300.0,
            participant_ids=[self.user2.id],
            description="Dinner"
        )

        self.assertIsNotNone(expense)
        self.assertEqual(error, "")
        self.assertEqual(expense.amount, 300.0)

        balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0]['user_id'], self.user2.id)
        self.assertAlmostEqual(balances[0]['amount'], 150.0, places=2)

        bob_balances = self.cf.get_user_balances(self.user2.id)
        self.assertAlmostEqual(bob_balances[0]['amount'], -150.0, places=2)

    def test_expense_three_people(self):
        """Alice pays 600 split with Bob and Charlie"""
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=600.0,
            participant_ids=[self.user2.id, self.user3.id],
            description="Groceries"
        )

        self.assertIsNotNone(expense)
        per_person = 600.0 / 3

        balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(balances), 2)

        bob_bal = next(b for b in balances if b['user_id'] == self.user2.id)
        self.assertAlmostEqual(bob_bal['amount'], per_person, places=2)
        charlie_bal = next(b for b in balances if b['user_id'] == self.user3.id)
        self.assertAlmostEqual(charlie_bal['amount'], per_person, places=2)

    def test_user_pays_for_themselves_rejected(self):
        """Edge case: user pays only for themselves"""
        result, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=100.0,
            participant_ids=[],
            description="Personal coffee"
        )

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("участник", error.lower())

    def test_payer_excluded_from_participants(self):
        """Edge case: payer accidentally included in participants"""
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=300.0,
            participant_ids=[self.user1.id, self.user2.id],
            description="Dinner"
        )

        self.assertIsNotNone(expense)
        balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(balances), 1)
        self.assertAlmostEqual(balances[0]['amount'], 150.0, places=2)

    def test_expense_with_category(self):
        """Expense with category and currency"""
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=500.0,
            participant_ids=[self.user2.id],
            description="Taxi",
            category="transport",
            currency="RUB",
        )

        self.assertIsNotNone(expense)
        self.assertEqual(expense.category, "transport")

    def test_expense_negative_amount(self):
        """Edge case: negative amount"""
        result, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=-100.0,
            participant_ids=[self.user2.id],
        )

        self.assertIsNone(result)
        self.assertIsNotNone(error)

    # ==================== SPLIT TYPE TESTS ====================

    def test_percent_split(self):
        """Test percentage-based split"""
        # Bob pays 60%, Charlie pays 40% of 1000
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=1000.0,
            split_type='percent',
            participant_ids=[self.user2.id, self.user3.id],
            shares={self.user2.id: 60, self.user3.id: 40},
            description="Percent split test"
        )

        self.assertIsNotNone(expense)
        self.assertEqual(error, "")

        balances = self.cf.get_user_balances(self.user1.id)
        bob_bal = next(b for b in balances if b['user_id'] == self.user2.id)
        charlie_bal = next(b for b in balances if b['user_id'] == self.user3.id)

        # Bob should owe ~600, Charlie ~400
        self.assertAlmostEqual(bob_bal['amount'], 600.0, places=1)
        self.assertAlmostEqual(charlie_bal['amount'], 400.0, places=1)

    def test_exact_split(self):
        """Test exact amount split"""
        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=1000.0,
            split_type='exact',
            participant_ids=[self.user2.id, self.user3.id],
            shares={self.user2.id: 700.0, self.user3.id: 200.0},
            description="Exact split test"
        )

        self.assertIsNotNone(expense)
        self.assertEqual(error, "")

        balances = self.cf.get_user_balances(self.user1.id)
        bob_bal = next(b for b in balances if b['user_id'] == self.user2.id)
        charlie_bal = next(b for b in balances if b['user_id'] == self.user3.id)

        # Bob owes 700, Charlie owes 200, Alice's share is 100
        self.assertAlmostEqual(bob_bal['amount'], 700.0, places=1)
        self.assertAlmostEqual(charlie_bal['amount'], 200.0, places=1)

    def test_percent_split_exceeds_100(self):
        """Edge case: percent split exceeds 100%"""
        result, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=1000.0,
            split_type='percent',
            participant_ids=[self.user2.id],
            shares={self.user2.id: 150},
        )

        self.assertIsNone(result)
        self.assertIsNotNone(error)

    # ==================== GROUP TESTS ====================

    def test_create_group(self):
        """Test creating a group"""
        group = self.cf.create_group("Квартира", self.user1.id, "Расходы на квартиру")
        self.assertIsNotNone(group)
        self.assertEqual(group.name, "Квартира")
        self.assertEqual(group.created_by, self.user1.id)
        self.assertFalse(group.is_archived)

    def test_group_members(self):
        """Test adding/removing group members"""
        group = self.cf.create_group("Test Group", self.user1.id)
        self.assertIsNotNone(group)

        # Add members
        success, msg = self.cf.add_group_member(group.id, self.user2.id)
        self.assertTrue(success)

        success, msg = self.cf.add_group_member(group.id, self.user3.id)
        self.assertTrue(success)

        members = self.cf.get_group_members(group.id)
        self.assertEqual(len(members), 3)  # creator + 2 added

        # Duplicate add
        success, msg = self.cf.add_group_member(group.id, self.user2.id)
        self.assertFalse(success)

    def test_user_groups(self):
        """Test getting user's groups"""
        group1 = self.cf.create_group("Group 1", self.user1.id)
        group2 = self.cf.create_group("Group 2", self.user1.id)
        self.cf.add_group_member(group1.id, self.user2.id)
        self.cf.add_group_member(group2.id, self.user2.id)

        alice_groups = self.cf.get_user_groups(self.user1.id)
        self.assertEqual(len(alice_groups), 2)

        bob_groups = self.cf.get_user_groups(self.user2.id)
        self.assertEqual(len(bob_groups), 2)

    def test_leave_group_no_balance(self):
        """Test leaving a group with no open balances"""
        group = self.cf.create_group("Test", self.user1.id)
        self.cf.add_group_member(group.id, self.user2.id)

        success, msg = self.cf.remove_group_member(group.id, self.user2.id)
        self.assertTrue(success)

        members = self.cf.get_group_members(group.id)
        self.assertEqual(len(members), 1)

    def test_leave_group_with_balance(self):
        """Edge case: can't leave group with open balance"""
        group = self.cf.create_group("Test", self.user1.id)
        self.cf.add_group_member(group.id, self.user2.id)

        # Create expense that creates balance
        self.cf.add_expense(
            payer_id=self.user1.id,
            amount=300.0,
            participant_ids=[self.user2.id],
            group_id=group.id,
        )

        success, msg = self.cf.remove_group_member(group.id, self.user2.id)
        self.assertFalse(success)
        self.assertIn("баланс", msg.lower())

    def test_archive_group(self):
        """Test archiving a group"""
        group = self.cf.create_group("Test", self.user1.id)

        success, msg = self.cf.archive_group(group.id, self.user1.id)
        self.assertTrue(success)

        # Verify archived
        g = self.cf.get_group(group.id)
        self.assertTrue(g.is_archived)

    def test_archive_group_not_creator(self):
        """Edge case: non-creator can't archive"""
        group = self.cf.create_group("Test", self.user1.id)

        success, msg = self.cf.archive_group(group.id, self.user2.id)
        self.assertFalse(success)

    def test_expense_in_group(self):
        """Test adding expense to a group"""
        group = self.cf.create_group("Квартира", self.user1.id)
        self.cf.add_group_member(group.id, self.user2.id)

        expense, error = self.cf.add_expense(
            payer_id=self.user1.id,
            amount=3000.0,
            participant_ids=[self.user2.id],
            description="Rent",
            group_id=group.id,
        )

        self.assertIsNotNone(expense)
        self.assertEqual(expense.group_id, group.id)

    def test_expense_non_member_in_group(self):
        """Edge case: expense by non-member in group"""
        group = self.cf.create_group("Test", self.user1.id)

        result, error = self.cf.add_expense(
            payer_id=self.user3.id,  # Not in group
            amount=100.0,
            participant_ids=[self.user1.id],
            group_id=group.id,
        )

        self.assertIsNone(result)
        self.assertIsNotNone(error)

    # ==================== SETTLEMENT TESTS ====================

    def test_full_settlement(self):
        """Test full debt settlement"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        success, message = self.cf.settle_balance(self.user2.id, self.user1.id)

        self.assertTrue(success)
        self.assertIn("полностью", message.lower())

        balances = self.cf.get_user_balances(self.user2.id)
        self.assertEqual(len(balances), 0)

    def test_partial_settlement(self):
        """Test partial debt settlement"""
        self.cf.add_expense(self.user1.id, 600.0, [self.user2.id], "Dinner")

        success, message = self.cf.settle_balance(self.user2.id, self.user1.id, 100.0)

        self.assertTrue(success)
        self.assertIn("осталось", message.lower())

        balances = self.cf.get_user_balances(self.user2.id)
        self.assertAlmostEqual(balances[0]['amount'], -200.0, places=2)

    def test_settlement_no_debt(self):
        """Edge case: settle when no debt"""
        success, message = self.cf.settle_balance(self.user2.id, self.user1.id)
        self.assertFalse(success)
        self.assertIn("нет долга", message.lower())

    def test_settlement_overpay(self):
        """Edge case: overpay settlement"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        # Bob owes 150, tries to pay 200
        success, message = self.cf.settle_balance(self.user2.id, self.user1.id, 200.0)

        self.assertTrue(success)
        balances = self.cf.get_user_balances(self.user2.id)
        self.assertEqual(len(balances), 0)  # Capped at actual debt

    def test_settlement_history(self):
        """Test settlement history"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")
        self.cf.settle_balance(self.user2.id, self.user1.id, 100.0)

        history = self.cf.get_settlement_history(user_id=self.user1.id)
        self.assertEqual(len(history), 1)
        self.assertAlmostEqual(history[0].amount, 100.0, places=2)

    # ==================== DELETE EXPENSE TESTS ====================

    def test_delete_expense_no_settlements(self):
        """Test deleting expense with no settlements"""
        expense, _ = self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        success, message = self.cf.delete_expense(expense.id)
        self.assertTrue(success)

        # Verify deleted
        expenses = self.cf.get_user_expenses(self.user1.id)
        self.assertEqual(len(expenses), 0)

    def test_delete_expense_with_settlements(self):
        """Edge case: can't delete expense with settlements"""
        expense, _ = self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")
        self.cf.settle_balance(self.user2.id, self.user1.id, 50.0)

        success, message = self.cf.delete_expense(expense.id)
        self.assertFalse(success)
        self.assertIn("погаш", message.lower())

    def test_delete_nonexistent_expense(self):
        """Edge case: delete nonexistent expense"""
        success, message = self.cf.delete_expense(99999)
        self.assertFalse(success)

    # ==================== EDIT EXPENSE TESTS ====================

    def test_edit_expense_amount(self):
        """Test editing expense amount"""
        expense, _ = self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        success, message = self.cf.edit_expense(expense.id, amount=500.0)
        self.assertTrue(success)

        updated = self.cf.get_expense(expense.id)
        self.assertAlmostEqual(updated.amount, 500.0, places=2)

    def test_edit_expense_description(self):
        """Test editing expense description"""
        expense, _ = self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Old desc")

        success, message = self.cf.edit_expense(expense.id, description="New desc")
        self.assertTrue(success)

        updated = self.cf.get_expense(expense.id)
        self.assertEqual(updated.description, "New desc")

    # ==================== BALANCE CALCULATION TESTS ====================

    def test_multiple_expenses_accumulate(self):
        """Test multiple expenses accumulate correctly"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner 1")
        self.cf.add_expense(self.user2.id, 200.0, [self.user1.id], "Lunch")

        balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(balances), 1)
        # Alice: Bob owes 150, Alice owes Bob 100 → Net: Bob owes Alice 50
        self.assertAlmostEqual(balances[0]['amount'], 50.0, places=2)

    def test_complex_three_person_scenario(self):
        """Complex scenario with 3 people"""
        # Alice pays 900 for groceries (300 each)
        self.cf.add_expense(self.user1.id, 900.0, [self.user2.id, self.user3.id], "Groceries")

        # Bob pays 600 for utilities (200 each)
        self.cf.add_expense(self.user2.id, 600.0, [self.user1.id, self.user3.id], "Utilities")

        # Charlie pays 300 for internet (100 each)
        self.cf.add_expense(self.user3.id, 300.0, [self.user1.id, self.user2.id], "Internet")

        # Alice's perspective:
        # Groceries: Bob owes 300, Charlie owes 300
        # Utilities: Alice owes Bob 200
        # Internet: Alice owes Charlie 100
        # Net: Bob owes Alice 100, Charlie owes Alice 200
        alice_balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(alice_balances), 2)

        bob_bal = next(b for b in alice_balances if b['user_id'] == self.user2.id)
        charlie_bal = next(b for b in alice_balances if b['user_id'] == self.user3.id)

        self.assertAlmostEqual(bob_bal['amount'], 100.0, places=2)
        self.assertAlmostEqual(charlie_bal['amount'], 200.0, places=2)

    def test_empty_balances(self):
        """Edge case: no expenses → empty balances"""
        balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(balances), 0)

    def test_balances_after_full_settlement(self):
        """Test balances clear after full settlement"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")
        self.cf.settle_balance(self.user2.id, self.user1.id)

        alice_balances = self.cf.get_user_balances(self.user1.id)
        self.assertEqual(len(alice_balances), 0)

    # ==================== OPTIMIZED SETTLEMENT TESTS ====================

    def test_optimized_settlement_simple(self):
        """Simple optimized settlement: A owes B"""
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        plan = self.cf.get_optimized_settlements()
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]['from_user_id'], self.user2.id)
        self.assertEqual(plan[0]['to_user_id'], self.user1.id)
        self.assertAlmostEqual(plan[0]['amount'], 150.0, places=2)

    def test_optimized_settlement_cycle(self):
        """Optimized settlement with a cycle"""
        # A owes B, B owes C, C owes A
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "A paid")  # B owes A 150
        self.cf.add_expense(self.user2.id, 300.0, [self.user3.id], "B paid")  # C owes B 150
        self.cf.add_expense(self.user3.id, 300.0, [self.user1.id], "C paid")  # A owes C 150

        plan = self.cf.get_optimized_settlements()
        # Should resolve to minimal transactions
        # Net: A: +150 - 150 = 0, B: -150 + 150 = 0, C: -150 + 150 = 0
        # All should be even!
        self.assertEqual(len(plan), 0)

    # ==================== ROUNDING TESTS ====================

    def test_rounding_100_div_3(self):
        """Test 100/3 rounding"""
        expense, _ = self.cf.add_expense(
            self.user1.id, 100.0, [self.user2.id, self.user3.id], "Pizza"
        )

        balances = self.cf.get_user_balances(self.user1.id)
        total_owed = sum(b['amount'] for b in balances)
        # Alice paid 100, her share is 33.33, so she should be owed ~66.67
        self.assertAlmostEqual(total_owed, 66.67, places=1)

    def test_rounding_preserves_total(self):
        """Test that rounding doesn't change total"""
        expense, _ = self.cf.add_expense(
            self.user1.id, 100.0, [self.user2.id, self.user3.id, self.user4.id], "Split 4 ways"
        )

        # Get all splits
        exp = self.cf.get_expense(expense.id)
        total_shares = sum(s.share for s in exp.splits)
        self.assertAlmostEqual(total_shares, 100.0, places=2)

    # ==================== USER TESTS ====================

    def test_register_existing_user(self):
        """Test registering same user twice"""
        user1_again = self.cf.register_user(1, "Alice Updated", "alice")
        self.assertEqual(user1_again.id, self.user1.id)

    def test_get_user_by_username(self):
        user = self.cf.get_user_by_username("bob")
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "Bob")

    def test_get_user_by_internal_id(self):
        user = self.cf.get_user_by_internal_id(self.user1.id)
        self.assertIsNotNone(user)
        self.assertEqual(user.telegram_id, 1)

    # ==================== PENDING USER TESTS ====================

    def test_pending_user_activation(self):
        pending = self.cf.register_pending_user("newuser")
        activated = self.cf.activate_pending_user("newuser", 12345, "New User")
        self.assertIsNotNone(activated)

        user = self.cf.get_user_by_username("newuser")
        self.assertEqual(user.telegram_id, 12345)
        self.assertEqual(user.first_name, "New User")

    def test_duplicate_pending_user(self):
        pending1 = self.cf.register_pending_user("newuser")
        pending2 = self.cf.register_pending_user("newuser")
        # Re-fetch to avoid detached instance
        p1 = self.cf.get_user_by_username("newuser")
        p2 = self.cf.get_user_by_username("newuser")
        self.assertEqual(p1.id, p2.id)

    # ==================== TELEGRAM LINK CODE TESTS ====================

    def test_generate_and_consume_link_code(self):
        code = self.cf.generate_link_code(self.user1.id)
        self.assertIsNotNone(code)
        self.assertEqual(len(code), 6)

        user = self.cf.consume_link_code(code, 99999, "Alice Tg")
        self.assertIsNotNone(user)
        # Re-fetch to avoid detached instance
        user = self.cf.get_user(99999)
        self.assertEqual(user.telegram_id, 99999)

    def test_consume_invalid_code(self):
        user = self.cf.consume_link_code("INVALID", 99999, "Someone")
        self.assertIsNone(user)

    def test_consume_expired_code(self):
        code = self.cf.generate_link_code(self.user1.id)
        # Manually expire it
        from database import TelegramLinkCode
        session = self.cf.db.get_session()
        link = session.query(TelegramLinkCode).filter_by(code=code).first()
        link.expires_at = datetime.utcnow() - timedelta(hours=1)
        session.commit()
        session.close()

        user = self.cf.consume_link_code(code, 99999, "Someone")
        self.assertIsNone(user)

    # ==================== FILTER TESTS ====================

    def test_filter_expenses_by_category(self):
        self.cf.add_expense(self.user1.id, 100.0, [self.user2.id], "Food", category="food")
        self.cf.add_expense(self.user1.id, 200.0, [self.user2.id], "Taxi", category="transport")

        food_expenses = self.cf.get_user_expenses(self.user1.id, category="food")
        self.assertEqual(len(food_expenses), 1)
        self.assertEqual(food_expenses[0].category, "food")

    def test_filter_expenses_by_date(self):
        date_from = datetime.utcnow() - timedelta(days=1)
        date_to = datetime.utcnow() + timedelta(days=1)

        self.cf.add_expense(self.user1.id, 100.0, [self.user2.id], "Recent")

        expenses = self.cf.get_user_expenses(
            self.user1.id, date_from=date_from, date_to=date_to
        )
        self.assertGreater(len(expenses), 0)

    def test_filter_expenses_by_group(self):
        group = self.cf.create_group("Test", self.user1.id)
        self.cf.add_group_member(group.id, self.user2.id)

        self.cf.add_expense(self.user1.id, 100.0, [self.user2.id], "Group expense", group_id=group.id)
        self.cf.add_expense(self.user1.id, 200.0, [self.user2.id], "Non-group expense")

        group_expenses = self.cf.get_group_expenses(group.id)
        self.assertEqual(len(group_expenses), 1)
        self.assertEqual(group_expenses[0].group_id, group.id)

    # ==================== TOTAL BALANCE TEST ====================

    def test_user_total_balance(self):
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        total = self.cf.get_user_total_balance(self.user1.id)
        self.assertAlmostEqual(total['total_owed'], 150.0, places=2)
        self.assertAlmostEqual(total['total_owes'], 0.0, places=2)
        self.assertAlmostEqual(total['net'], 150.0, places=2)

    # ==================== WEEKLY DIGEST TEST ====================

    def test_weekly_digest(self):
        self.cf.add_expense(self.user1.id, 300.0, [self.user2.id], "Dinner")

        digest = self.cf.get_weekly_digest(self.user1.id)
        self.assertEqual(digest['user_id'], self.user1.id)
        self.assertGreater(len(digest['recent_expenses']), 0)

    # ==================== CATEGORIES & CURRENCIES ====================

    def test_get_categories(self):
        categories = self.cf.get_categories()
        self.assertGreater(len(categories), 0)
        self.assertIn('food', [c['value'] for c in categories])

    def test_get_currencies(self):
        currencies = self.cf.get_currencies()
        self.assertIn('RUB', currencies)
        self.assertIn('USD', currencies)


if __name__ == '__main__':
    unittest.main()
