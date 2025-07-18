import io
import unittest
import os
from contextlib import redirect_stdout
from particle_converter import SinsParticle


class TestParticle(unittest.TestCase):
    def setUp(self):
        curr_path = os.path.dirname(os.path.abspath(__file__))
        self.particles_path = os.path.join(curr_path, "particles/")
        self.test_1 = SinsParticle(self.particles_path + "test_1.particle")
        self.test_2 = SinsParticle(self.particles_path + "test_2.particle")
        self.test_3 = SinsParticle(self.particles_path + "test_3.particle")

    def test_emitters(self):
        self.test_1.parse()
        self.assertEqual(len(self.test_1.emitters), 10)
        self.assertEqual(self.test_1.emitters[0]["name"], "half1")
        self.assertEqual(self.test_1.emitters[0]["emit_rate"]["primary_emit_rate"], [20.0, 20.0])

        self.test_2.parse()
        self.assertEqual(self.test_2.emitters[3]["name"], "cloud out small")
        self.assertEqual(self.test_2.emitters[-1]["name"], "sparks 5")
        self.assertEqual(
            self.test_2.emitters[-1]["emit_rate"]["primary_emit_rate"], [250.0, 250.0]
        )
        self.assertEqual(self.test_2.emitters[-2]["radial_velocity"], [200.0, 800.0])
        self.assertNotIn("texture_0", self.test_2.emitters[-3])
        self.assertNotIn("texture_1", self.test_2.emitters[-3])
        self.assertEqual(
            self.test_2.emitters[-3]["particle"]["billboard"]["facing_type"],
            "face_camera_by_rotating_on_particle_direction",
        )
        self.assertEqual(self.test_2.emitters[-1]["particle"]["billboard"]["rotation"], [0.0, 0.0])
        self.assertEqual(
            self.test_2.emitters[-1]["particle"]["billboard"]["rotation_speed"], [0.0, 0.0]
        )
        self.assertEqual(self.test_2.emitters[-5]["angle_variance"], [3.141593, 3.141593])
        self.assertNotIn("emit_duration", self.test_2.emitters[-5])

    def test_modifiers(self):
        self.test_1.parse()
        modifiers = self.test_1.modifiers
        self.assertEqual(len(modifiers), 11)
        self.assertEqual(modifiers[0]["name"], "Force Cloud down")
        self.assertIn("(copy) (new) Sphere-1-2", self.test_1.fade_values)
        self.assertTrue(self.test_1.fade_values["(copy) (new) Sphere-1-2"]["fade_in_enabled"])
        self.assertEqual(modifiers[2]["point"], [0.000000, -130.00000, 0.000000])
        self.assertEqual(modifiers[1]["width_change_rate"], [-30.0, -30.0])
        self.assertEqual(modifiers[1]["height_change_rate"], [-30.0, -30.0])
        self.assertEqual(modifiers[0]["particle_time_offset"], [0.3, 0.3])
        self.test_2.parse()
        modifiers = self.test_2.modifiers
        self.assertEqual(modifiers[-1]["name"], "Ray out")
        self.assertNotIn("particle_time_offset", modifiers[-1])
        self.assertEqual(modifiers[-1]["width_change_rate"], [100.0, 100.0])
        self.assertEqual(modifiers[-1]["height_change_rate"], [400.0, 400.0])

    def test_emitter_attachments(self):
        self.test_1.parse()
        self.assertEqual(len(self.test_1.emitter_to_node_attachments), 10)

        self.assertEqual(self.test_1.modifier_to_emitter_attachments[5]["attacher_id"], 14)
        self.assertEqual(self.test_1.modifier_to_emitter_attachments[1]["attacher_id"], 1)

    def assertEmitterEqual(self, parsed, original, original_emitter_type):
        self.assertEqual(original["Name"], parsed["name"])
        self.assertEqual(original["Enabled"], parsed["is_visible"])
        self.assertEqual([original["EmitRate"]] * 2, parsed["emit_rate"]["primary_emit_rate"])
        self.assertEqual([original["ParticleStartMass"]] * 2, parsed["particle"]["mass"])
        self.assertEqual(original["ParticleStartColor"], parsed["particle"]["color"])
        self.assertEqual([original["ParticleWidth"]] * 2, parsed["particle"]["billboard"]["width"])
        self.assertEqual(
            [original["ParticleHeight"]] * 2, parsed["particle"]["billboard"]["height"]
        )
        if original["MeshName"]:
            self.assertEqual(original["MeshName"], parsed["particle"]["mesh"]["mesh"])

        if not original["HasInfiniteEmitCount"]:
            self.assertEqual(
                list(map(int, [original["MaxEmitCount"]] * 2)), parsed["emit_max_particle_count"]
            )

        self.assertEqual([original["ParticleLifeTime"]] * 2, parsed["particle"]["max_duration"])
        if original_emitter_type == "Point":
            self.assertEqual(
                [original["ParticleMinStartLinearSpeed"], original["ParticleMaxStartLinearSpeed"]],
                parsed["forward_velocity"],
            )
        if original["ParticlesRotate"]:
            self.assertEqual(
                list(
                    map(
                        abs,
                        [
                            original["ParticleMinStartAngularSpeed"],
                            original["ParticleMaxStartAngularSpeed"],
                        ],
                    )
                ),
                list(map(abs, parsed["particle"]["billboard"]["rotation_speed"])),
            )

            self.assertEqual(
                list(
                    map(
                        abs,
                        [
                            original["ParticleMinStartRotation"],
                            original["ParticleMaxStartRotation"],
                        ],
                    )
                ),
                list(map(abs, parsed["particle"]["billboard"]["rotation"])),
            )

    def assertModifierEqual(self, parsed, original):
        if original["Name"] != "":
            self.assertEqual(original["Name"], parsed["name"])
        self.assertEqual([original["StartTime"]] * 2, parsed["start_delay"])
        if {"MinForce", "MaxForce"} <= original.keys():
            self.assertEqual(
                [original["MinForce"] / 25, original["MaxForce"] / 25],
                parsed["force"]["range"],
            )
            if "Direction" in original:
                self.assertEqual(original["Direction"], parsed["direction"])
            if "Point" in original:
                self.assertEqual(original["Point"], parsed["point"])
        if {"WidthInflateRate", "HeightInflateRate"} <= original.keys():
            self.assertEqual(
                [original["WidthInflateRate"]] * 2,
                parsed["width_change_rate"],
            )
            self.assertEqual(
                [original["HeightInflateRate"]] * 2,
                parsed["height_change_rate"],
            )
        if {
            "Radius",
            "AxisOfRotation",
            "AxisOrigin",
            "AngularVelocity",
        } <= original.keys():
            self.assertEqual(
                [original["AngularVelocity"]] * 2,
                parsed["angular_velocity"],
            )
            self.assertEqual([original["Radius"]] * 2, parsed["radius"])
            self.assertEqual(original["AxisOfRotation"], parsed["axis_of_rotation"])
            self.assertEqual(original["AxisOrigin"], parsed["axis_origin"])
        if {"Point", "Distance"} <= original.keys():
            self.assertEqual(original["Point"], parsed["point"])
            self.assertEqual([original["Distance"]] * 2, parsed["tolerance"])
        if {"MinWidth", "MaxWidth", "MinHeight", "MaxHeight"} <= original.keys():
            self.assertEqual(
                [original["MinWidth"], original["MaxWidth"]],
                parsed["width_stop"],
            )
            self.assertEqual(
                [original["MinHeight"], original["MaxHeight"]],
                parsed["height_stop"],
            )
        if {
            "TransitionPeriod",
            "StartColor",
            "StartAlpha",
            "EndColor",
            "EndAlpha",
        } <= original.keys():
            self.assertEqual(
                [original["TransitionPeriod"]] * 2,
                parsed["change_duration"],
            )
            self.assertEqual(original["StartColor"], parsed["begin_color"])
            self.assertEqual(original["EndColor"], parsed["end_color"])
        if {"DragCoefficient"} <= original.keys():
            self.assertEqual(
                [original["DragCoefficient"]] * 2,
                parsed["coefficient_generator"]["range"],
            )
        if {"JitterForce", "UseCommonForce"} <= original.keys():
            self.assertEqual([original["JitterForce"]] * 2, parsed["force"]["range"])
            if original["UseCommonForce"]:
                self.assertEqual(
                    original["UseCommonForce"],
                    parsed["is_random_jitter_shared"],
                )

    def test_all_particles(self):
        for _particle in [f for f in os.listdir(self.particles_path) if f.endswith(".particle")]:
            with self.subTest(_particle):
                with io.StringIO() as buf, redirect_stdout(buf):
                    particle = SinsParticle(
                        particle_path=os.path.join(self.particles_path, _particle)
                    ).parse()
                    if "Failed to parse" in buf.getvalue():
                        self.assertNotIn("Failed to parse", buf.getvalue())

                modifiers = particle.modifiers
                collector_modifiers = particle.collector["ParticleSimulation"]["Affectors"]

                emitters = particle.emitters
                collector_emitters = particle.collector["ParticleSimulation"]["Emitters"]

                for i, c_modifier in enumerate(
                    [f for f in collector_modifiers if f["AffectorType"] != "Fade"]
                ):
                    with self.subTest(mod_idx=i, particle=_particle):
                        self.assertModifierEqual(modifiers[i], c_modifier["AffectorContents"])
                for i, c_emitter in enumerate(collector_emitters):
                    with self.subTest(emit_idx=i, particle=_particle):
                        self.assertEmitterEqual(
                            emitters[i], c_emitter["EmitterContents"], c_emitter["EmitterType"]
                        )


if __name__ == "__main__":
    unittest.main()
