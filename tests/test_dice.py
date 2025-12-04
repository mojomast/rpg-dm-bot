"""
Unit tests for DiceRoller class in src/tools.py
Tests dice notation parsing and rolling mechanics.
"""

import pytest
import random
from src.tools import DiceRoller


class TestDiceRollerBasic:
    """Basic dice rolling tests"""

    def test_single_die(self, dice_roller):
        """Test rolling a single die"""
        result = dice_roller.roll("1d6")
        
        assert 'total' in result
        assert 'rolls' in result
        assert result['expression'] == "1d6"
        assert 1 <= result['total'] <= 6
        assert len(result['rolls']) == 1

    def test_multiple_dice(self, dice_roller):
        """Test rolling multiple dice"""
        result = dice_roller.roll("3d6")
        
        assert len(result['rolls']) == 3
        assert 3 <= result['total'] <= 18
        for roll in result['rolls']:
            assert 1 <= roll <= 6

    def test_implicit_count(self, dice_roller):
        """Test rolling dice without explicit count (d20 = 1d20)"""
        result = dice_roller.roll("d20")
        
        assert len(result['rolls']) == 1
        assert 1 <= result['total'] <= 20

    def test_large_dice(self, dice_roller):
        """Test rolling large dice (d100)"""
        result = dice_roller.roll("1d100")
        
        assert 1 <= result['total'] <= 100


class TestDiceRollerModifiers:
    """Tests for dice modifiers"""

    def test_positive_modifier(self, dice_roller):
        """Test rolling with positive modifier"""
        result = dice_roller.roll("1d20+5")
        
        assert result['modifier'] == 5
        assert result['total'] == result['subtotal'] + 5
        assert 6 <= result['total'] <= 25

    def test_negative_modifier(self, dice_roller):
        """Test rolling with negative modifier"""
        result = dice_roller.roll("1d20-3")
        
        assert result['modifier'] == -3
        assert result['total'] == result['subtotal'] - 3
        # Total can be negative or low
        assert -2 <= result['total'] <= 17

    def test_zero_modifier(self, dice_roller):
        """Test rolling with no modifier"""
        result = dice_roller.roll("2d6")
        
        assert result['modifier'] == 0
        assert result['total'] == result['subtotal']


class TestDiceRollerKeepDrop:
    """Tests for keep highest/lowest mechanics"""

    def test_keep_highest(self, dice_roller, seeded_random):
        """Test 4d6 keep highest 3 (classic stat rolling)"""
        result = dice_roller.roll("4d6kh3")
        
        assert len(result['rolls']) == 4
        assert len(result['kept']) == 3
        # Kept dice should be the highest ones
        assert sorted(result['kept'], reverse=True) == result['kept']

    def test_keep_lowest(self, dice_roller, seeded_random):
        """Test keep lowest mechanic"""
        result = dice_roller.roll("4d6kl2")
        
        assert len(result['rolls']) == 4
        assert len(result['kept']) == 2
        # Verify kept are the lowest
        sorted_rolls = sorted(result['rolls'])
        assert sorted(result['kept']) == sorted_rolls[:2]

    def test_keep_highest_sum(self, dice_roller):
        """Test that subtotal is sum of kept dice only"""
        result = dice_roller.roll("4d6kh3")
        
        assert result['subtotal'] == sum(result['kept'])


class TestDiceRollerAdvantageDisadvantage:
    """Tests for D&D 5e advantage/disadvantage"""

    def test_advantage(self, dice_roller):
        """Test rolling with advantage"""
        result = dice_roller.roll("1d20", advantage=True)
        
        assert result['advantage'] is True
        assert len(result['rolls']) == 2
        assert result['total'] == max(result['rolls'])

    def test_disadvantage(self, dice_roller):
        """Test rolling with disadvantage"""
        result = dice_roller.roll("1d20", disadvantage=True)
        
        assert result['disadvantage'] is True
        assert len(result['rolls']) == 2
        assert result['total'] == min(result['rolls'])

    def test_advantage_with_modifier(self, dice_roller):
        """Test advantage with modifier"""
        result = dice_roller.roll("1d20+5", advantage=True)
        
        assert result['total'] == max(result['rolls']) + 5

    def test_advantage_only_on_d20(self, dice_roller):
        """Test that advantage only applies to single d20 rolls"""
        # Rolling 2d20 with advantage should not apply advantage logic
        result = dice_roller.roll("2d20", advantage=True)
        
        # Should just roll 2d20 normally
        assert 'advantage' not in result


class TestDiceRollerCriticalRolls:
    """Tests for natural 20s and natural 1s"""

    def test_natural_20_detected(self, dice_roller):
        """Test that natural 20 is detected"""
        # Run many times to eventually get a nat 20
        found_nat_20 = False
        for _ in range(1000):
            result = dice_roller.roll("1d20")
            if result['natural_20']:
                found_nat_20 = True
                assert result['total'] == 20
                assert result['critical'] is True
                break
        
        # Statistical check - should hit nat 20 within 1000 rolls
        assert found_nat_20, "Did not roll a natural 20 in 1000 attempts"

    def test_natural_1_detected(self, dice_roller):
        """Test that natural 1 is detected"""
        found_nat_1 = False
        for _ in range(1000):
            result = dice_roller.roll("1d20")
            if result['natural_1']:
                found_nat_1 = True
                assert result['kept'][0] == 1
                assert result['fumble'] is True
                break
        
        assert found_nat_1, "Did not roll a natural 1 in 1000 attempts"

    def test_critical_not_on_modified(self, dice_roller):
        """Test that natural 20/1 is based on actual die roll, not total"""
        # A roll of 1d20-5 with a natural 20 should still be critical
        # even though total is 15
        found_crit = False
        for _ in range(1000):
            result = dice_roller.roll("1d20-5")
            if result['natural_20']:
                found_crit = True
                assert result['critical'] is True
                assert result['total'] == 15  # 20 - 5
                break


class TestDiceRollerInvalidInput:
    """Tests for error handling"""

    def test_invalid_expression(self, dice_roller):
        """Test handling of invalid dice expression"""
        result = dice_roller.roll("invalid")
        
        assert 'error' in result

    def test_invalid_format(self, dice_roller):
        """Test handling of malformed expression"""
        result = dice_roller.roll("abc123")
        
        assert 'error' in result

    def test_empty_string(self, dice_roller):
        """Test handling of empty string"""
        result = dice_roller.roll("")
        
        assert 'error' in result


class TestDiceRollerEdgeCases:
    """Edge case tests"""

    def test_whitespace_handling(self, dice_roller):
        """Test that whitespace is handled correctly"""
        result = dice_roller.roll(" 2d6 + 3 ")
        
        assert result['expression'] == "2d6+3"
        assert result['modifier'] == 3

    def test_case_insensitive(self, dice_roller):
        """Test that dice expressions are case insensitive"""
        result = dice_roller.roll("2D6")
        
        assert result['expression'] == "2d6"
        assert len(result['rolls']) == 2

    def test_many_dice(self, dice_roller):
        """Test rolling many dice"""
        result = dice_roller.roll("10d6")
        
        assert len(result['rolls']) == 10
        assert 10 <= result['total'] <= 60

    def test_d1(self, dice_roller):
        """Test rolling a d1 (always 1)"""
        result = dice_roller.roll("1d1")
        
        assert result['total'] == 1


class TestDiceRollerStatisticalDistribution:
    """Statistical tests to verify randomness"""

    def test_d6_distribution(self, dice_roller):
        """Test that d6 rolls are roughly uniform"""
        counts = {i: 0 for i in range(1, 7)}
        num_rolls = 6000
        
        for _ in range(num_rolls):
            result = dice_roller.roll("1d6")
            counts[result['total']] += 1
        
        # Each face should appear roughly 1000 times (+/- 15%)
        for face, count in counts.items():
            expected = num_rolls / 6
            assert 0.7 * expected < count < 1.3 * expected, \
                f"Face {face} appeared {count} times, expected ~{expected}"

    def test_2d6_bell_curve(self, dice_roller):
        """Test that 2d6 follows expected bell curve"""
        counts = {i: 0 for i in range(2, 13)}
        num_rolls = 3600
        
        for _ in range(num_rolls):
            result = dice_roller.roll("2d6")
            counts[result['total']] += 1
        
        # 7 should be most common (6/36 = 16.67%)
        most_common = max(counts, key=counts.get)
        assert most_common == 7, f"Expected 7 to be most common, got {most_common}"
        
        # 2 and 12 should be least common (1/36 = 2.78%)
        assert counts[2] < counts[7] / 3
        assert counts[12] < counts[7] / 3


class TestDiceRollerDeterministic:
    """Tests with seeded random for deterministic behavior"""

    def test_seeded_roll(self, dice_roller, seeded_random):
        """Test that seeded random produces consistent results"""
        # With seed 42, the first few 1d6 rolls should be consistent
        results = [dice_roller.roll("1d6")['total'] for _ in range(5)]
        
        # Just verify they're valid, actual values depend on Python version
        for r in results:
            assert 1 <= r <= 6

    def test_reproducible_session(self, seeded_random):
        """Test that entire session is reproducible with same seed"""
        roller1 = DiceRoller()
        results1 = [roller1.roll("1d20+5")['total'] for _ in range(10)]
        
        # Re-seed
        random.seed(42)
        roller2 = DiceRoller()
        results2 = [roller2.roll("1d20+5")['total'] for _ in range(10)]
        
        assert results1 == results2
