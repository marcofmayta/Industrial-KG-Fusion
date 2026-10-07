import unittest
from tools.automatic_relevance_review import screen_pair


class ScreeningTests(unittest.TestCase):
    def test_absent_action_cannot_be_useful(self):
        grade,_,_ = screen_pair('Motor M-01 bearing fault.', 'Motor M-02 bearing fault.', '')
        self.assertLess(grade,2)

    def test_different_equipment_cannot_be_promoted(self):
        grade,_,_ = screen_pair('Motor M-01 bearing fault.', 'Pump P-02 bearing fault.', 'Replace bearing.')
        self.assertEqual(grade,0)

    def test_equivalent_problem_remains_provisional(self):
        grade,_,_ = screen_pair('Motor M-01 bearing fault.', 'Motor M-02 bearing fault.', 'Replace bearing.')
        self.assertEqual(grade,2)
