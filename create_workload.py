from pathlib import Path 

def create_input_files_from_to_create(to_create_path: Path, inputs_dir: Path):
    inputs_dir.mkdir(parents=True, exist_ok=True)

    with to_create_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            name, size_str = line.split()
            size = int(size_str)

            fp = inputs_dir / name
            print(f"[INIT] Creating {fp} size={size} bytes")
            with fp.open("wb") as fout:
                fout.truncate(size)


if __name__ == "__main__":
    workflow_id = "MyDAG-synthetic-instance"
    bench_dir = Path(f"./tmp")

    bench_json = bench_dir / "mydag-synthetic-instance-30.json"  # f"{workflow_id}.json"
    to_create = bench_dir / "to_create.txt"
    inputs_dir = bench_dir / "inputs"

    create_input_files_from_to_create(to_create, inputs_dir)

