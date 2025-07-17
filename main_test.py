import unittest
import os
from main import SinsParticle


class TestParticle(unittest.TestCase):
    test_1 = SinsParticle(os.path.join("src", "tests", "test_1.particle")).parse()
    test_2 = SinsParticle(os.path.join("src", "tests", "test_2.particle")).parse()

    def test_emitters(self):
        self.assertEqual(len(self.test_1.emitters), 10)
        self.assertEqual(self.test_1.emitters[0]["name"], "half1")
        self.assertEqual(self.test_1.emitters[0]["emit_rate"]["primary_emit_rate"], [20.0, 20.0])

        self.assertEqual(self.test_2.emitters[3]["name"], "cloud out small")
        self.assertEqual(self.test_2.emitters[-1]["name"], "sparks 5")
        self.assertEqual(self.test_2.emitters[-1]["emit_rate"]["primary_emit_rate"],  [250.0, 250.0])
        self.assertEqual(self.test_2.emitters[-2]["radial_velocity"],  [200.0, 800.0])
        self.assertNotIn("texture_0",  self.test_2.emitters[-3])
        self.assertNotIn("texture_1",  self.test_2.emitters[-3])
        self.assertEqual(self.test_2.emitters[-3]["particle"]["billboard"]["facing_type"],
                         "face_camera_by_rotating_on_particle_direction")
        self.assertEqual(self.test_2.emitters[-1]["particle"]["billboard"]["rotation"], [0.0, 0.0])
        self.assertEqual(self.test_2.emitters[-1]["particle"]["billboard"]["rotation_speed"], [0.0, 0.0])
        self.assertEqual(self.test_2.emitters[-5]["angle_variance"], [3.141593, 3.141593])
        self.assertNotIn("emit_duration", self.test_2.emitters[-5])

    def test_modifiers(self):
        modifiers = self.test_1.modifiers
        self.assertEqual(len(modifiers), 11)
        self.assertEqual(modifiers[0]["name"], "Force Cloud down")
        self.assertIn("(copy) (new) Sphere-1-2", self.test_1.fade_values)
        self.assertTrue(self.test_1.fade_values["(copy) (new) Sphere-1-2"]["fade_in_enabled"])
        self.assertEqual(modifiers[2]["point"], [0.000000, -130.00000, 0.000000])
        self.assertEqual(modifiers[1]["width_change_rate"], [-30.0, -30.0])
        self.assertEqual(modifiers[1]["height_change_rate"], [-30.0, -30.0])
        self.assertEqual(modifiers[0]["particle_time_offset"], [0.3, 0.3])
        modifiers = self.test_2.modifiers
        self.assertEqual(modifiers[-1]["name"], "Ray out")
        self.assertNotIn("particle_time_offset", modifiers[-1])
        self.assertEqual(modifiers[-1]["width_change_rate"], [100.0, 100.0])
        self.assertEqual(modifiers[-1]["height_change_rate"], [400.0, 400.0])

    def test_emitter_attachments(self):
        self.assertEqual(len(self.test_1.emitter_to_node_attachments), 10)

        self.assertEqual(self.test_1.modifier_to_emitter_attachments[5]["attacher_id"], 14)
        self.assertEqual(self.test_1.modifier_to_emitter_attachments[1]["attacher_id"], 1)


if __name__ == "__main__":
    unittest.main()
