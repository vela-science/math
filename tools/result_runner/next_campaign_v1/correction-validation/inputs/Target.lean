import FormalConjecturesForMathlib

namespace ResultRunnerQualification

theorem source_native {a b c : ℕ} : a ∣ b + c * a ↔ a ∣ b :=
  Nat.dvd_add_mul_self

end ResultRunnerQualification
