import FormalConjecturesForMathlib

namespace ResultRunnerQualification

theorem source_native {a b c : ℕ} : a ∣ b + c * a ↔ a ∣ b :=
  Nat.dvd_add_mul_self

end ResultRunnerQualification

example : ∀ {a b c : ℕ}, a ∣ b + c * a ↔ a ∣ b
 := by exact ResultRunnerQualification.source_native
#print axioms ResultRunnerQualification.source_native
