"""Console worker used only by the desktop process; no Python installation needed."""
import runpy
import sys


def main():
    from runtime import hold_instance_mutex
    hold_instance_mutex()
    stages = {"main", "process_incoming", "load_sales", "generate_reports"}
    if len(sys.argv) < 3 or sys.argv[1] != "--stage" or sys.argv[2] not in stages:
        raise SystemExit("Expected --stage followed by a supported ETL stage")
    stage = sys.argv[2]
    sys.argv = [stage] + sys.argv[3:]
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    runpy.run_module(stage, run_name="__main__")


if __name__ == "__main__":
    main()
