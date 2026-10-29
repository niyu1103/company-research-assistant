import subprocess
import sys
from pathlib import Path


EVALUATIONS = [
    (
        "RETRIEVAL",
        "evaluate_retrieval.py",
    ),
    (
        "CONTEXT SUFFICIENCY",
        "evaluate_context_sufficiency.py",
    ),
    (
        "GROUNDEDNESS",
        "evaluate_groundedness_cases.py",
    ),
    (
        "ANSWER RELEVANCE",
        "evaluate_answer_relevance_qa.py",
    ),
     (
        "QA SUFFICIENCY ALIGNMENT",
        "evaluate_qa_sufficiency_alignment.py",
    ),
]


def main() -> None:
    scripts_dir = Path(__file__).resolve().parent

    failed_evaluations: list[str] = []

    for name, script_name in EVALUATIONS:
        print()
        print("#" * 80)
        print(name)
        print("#" * 80)

        script_path = scripts_dir / script_name

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
            ],
            check=False,
        )

        if result.returncode != 0:
            failed_evaluations.append(name)

    print()
    print("=" * 80)
    print("FULL EVALUATION SUMMARY")
    print("=" * 80)

    for name, _ in EVALUATIONS:
        status = (
            "FAIL"
            if name in failed_evaluations
            else "PASS"
        )

        print(f"{name}: {status}")

    if failed_evaluations:
        raise SystemExit(1)

    print()
    print("ALL EVALUATIONS PASSED")


if __name__ == "__main__":
    main()