import io
import unittest
import os
from contextlib import redirect_stdout
from typing import Any
from particle_converter import SinsParticle


class TestParticle(unittest.TestCase):
    def setUp(self) -> None:
        curr_path = os.path.dirname(os.path.abspath(__file__))
        self.particles_path = os.path.join(curr_path, "particles/")

    def assertEmitterEqual(self, parsed: Any, original: Any, original_emitter_type: Any) -> None:
        self.assertEqual(original["Name"], parsed["name"])
        self.assertEqual(original["Enabled"], parsed["is_visible"])
        self.assertEqual(
            [original["EmitRate"]] * 2,
            parsed["emit_rate"]["primary_emit_rate"],
        )
        self.assertEqual([original["ParticleStartMass"]] * 2, parsed["particle"]["mass"])
        self.assertEqual(original["ParticleStartColor"], parsed["particle"]["color"])
        self.assertEqual(
            [original["ParticleWidth"]] * 2,
            parsed["particle"]["billboard"]["width"],
        )
        self.assertEqual(
            [original["ParticleHeight"]] * 2,
            parsed["particle"]["billboard"]["height"],
        )
        if original["MeshName"]:
            self.assertEqual(original["MeshName"], parsed["particle"]["mesh"]["mesh"])

        if not original["HasInfiniteEmitCount"]:
            self.assertEqual(
                list(map(int, [original["MaxEmitCount"]] * 2)),
                parsed["emit_max_particle_count"],
            )

        self.assertEqual(
            [original["ParticleLifeTime"]] * 2,
            parsed["particle"]["max_duration"],
        )
        if original_emitter_type == "Point":
            self.assertEqual(
                [
                    original["ParticleMinStartLinearSpeed"],
                    original["ParticleMaxStartLinearSpeed"],
                ],
                parsed["forward_velocity"],
            )
        if original["ParticlesRotate"]:
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

    def assertModifierEqual(self, parsed: Any, original: Any) -> None:
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
        if {
            "MinWidth",
            "MaxWidth",
            "MinHeight",
            "MaxHeight",
        } <= original.keys():
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

    def test_all_particles(self) -> None:
        for _particle in [f for f in os.listdir(self.particles_path) if f.endswith(".particle")]:
            with self.subTest(_particle):
                with io.StringIO() as buf, redirect_stdout(buf):
                    particle = SinsParticle(
                        particle_path=os.path.join(self.particles_path, _particle)
                    ).parse()
                    if "Failed to parse" in buf.getvalue():
                        self.assertNotIn("Failed to parse", buf.getvalue())

                modifiers = particle.file["modifiers"]  # type: ignore
                collector_modifiers = particle.collector["ParticleSimulation"]["Affectors"]

                emitters = particle.file["emitters"]  # type: ignore
                collector_emitters = particle.collector["ParticleSimulation"]["Emitters"]

                for i, c_modifier in enumerate(
                    [f for f in collector_modifiers if f["AffectorType"] != "Fade"]
                ):
                    with self.subTest(mod_idx=i, particle=_particle):
                        self.assertModifierEqual(modifiers[i], c_modifier["AffectorContents"])
                for i, c_emitter in enumerate(collector_emitters):
                    with self.subTest(emit_idx=i, particle=_particle):
                        self.assertEmitterEqual(
                            emitters[i],
                            c_emitter["EmitterContents"],
                            c_emitter["EmitterType"],
                        )


if __name__ == "__main__":
    unittest.main()
