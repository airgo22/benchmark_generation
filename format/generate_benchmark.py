from pathlib import Path
from dataclasses import dataclass, asdict
import json
import shutil
import subprocess

from wfcommons.wfbench import WorkflowBenchmark, DaskTranslator
from wfcommons import WorkflowGenerator
from my_recipe import MyRecipe


import json

def load_experiments(config_path: Path):
    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    experiments = []

    for exp in cfg["experiments"]:
        experiments.append(
            ExperimentConfig(
                name=exp["name"],
                shape=WorkflowShapeConfig(**exp["shape"]),
                load=LoadConfig(**exp["load"]),
                repeat=exp.get("repeat", 1),
                convert_to_test=exp.get("convert_to_test", True),
                translate_to_dask=exp.get("translate_to_dask", False),
            )
        )

    return experiments

@dataclass
class WorkflowShapeConfig:
    muban: str
    num_tasks: int
    runtime_factor: float
    input_file_size_factor: float
    output_file_size_factor: float
    num_layers: int
    sigma: float
    edge_prob: float


@dataclass
class LoadConfig:
    cpu_work: int
    percent_cpu: float
    data: int | None = None   # 可选，不想显式设 data 就传 None


@dataclass
class ExperimentConfig:
    name: str
    shape: WorkflowShapeConfig
    load: LoadConfig
    repeat: int = 1
    convert_to_test: bool = True
    translate_to_dask: bool = False


def build_recipe(shape: WorkflowShapeConfig):
    return MyRecipe.from_num_tasks(
        muban=shape.muban,
        num_tasks=shape.num_tasks,
        runtime_factor=shape.runtime_factor,
        input_file_size_factor=shape.input_file_size_factor,
        output_file_size_factor=shape.output_file_size_factor,
        num_layers=shape.num_layers,
        sigma=shape.sigma,
        edge_prob=shape.edge_prob,
    )


def make_case_name(exp: ExperimentConfig, run_idx: int) -> str:
    s = exp.shape
    l = exp.load
    return (
        f"{exp.name}_"
        f"{s.muban}_n{s.num_tasks}_"
        f"layer{s.num_layers}_sigma{s.sigma}_edge{s.edge_prob}_"
        f"cpu{l.cpu_work}_pc{str(l.percent_cpu).replace('.', '')}_"
        f"run{run_idx:02d}"
    )


def save_json(obj, path: Path):
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def convert_benchmark_to_test(benchmark_json: Path, test_json: Path):
    cmd = [
        "python",
        "trans_benchmark.py",
        "-i", str(benchmark_json),
        "-o", str(test_json),
        "-n", "test"
    ]
    subprocess.run(cmd, check=True)


def generate_one_case(exp: ExperimentConfig, run_idx: int, base_dir: Path):
    case_name = make_case_name(exp, run_idx)
    case_dir = base_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)

    # 1) 构造 recipe / generator
    recipe = build_recipe(exp.shape)
    generator = WorkflowGenerator(recipe)

    # 2) 生成 synthetic workflow
    workflow = generator.build_workflow()

    # 保存 workflow instance，便于回溯
    workflow_json = case_dir / f"{case_name}_workflow.json"
    workflow.write_json(workflow_json)

    # 3) 生成 benchmark
    benchmark = WorkflowBenchmark(recipe=MyRecipe, num_tasks=exp.shape.num_tasks)

    if exp.load.data is None:
        benchmark_path = benchmark.create_benchmark_from_synthetic_workflow(
            case_dir,
            workflow,
            cpu_work=exp.load.cpu_work,
            percent_cpu=exp.load.percent_cpu,
        )
    else:
        benchmark_path = benchmark.create_benchmark_from_synthetic_workflow(
            case_dir,
            workflow,
            cpu_work=exp.load.cpu_work,
            percent_cpu=exp.load.percent_cpu,
            data=exp.load.data,
        )

    # 4) 重命名 benchmark 文件
    # create_benchmark_from_synthetic_workflow 返回生成出来的 benchmark 路径
    # 你可以把它统一改名成更清楚的名字
    benchmark_json = case_dir / f"{case_name}_benchmark.json"
    if Path(benchmark_path) != benchmark_json:
        shutil.move(str(benchmark_path), str(benchmark_json))

    # 5) 保存本次实验配置，方便以后复现实验
    meta = {
        "case_name": case_name,
        "shape": asdict(exp.shape),
        "load": asdict(exp.load),
        "repeat_index": run_idx,
    }
    save_json(meta, case_dir / f"{case_name}_meta.json")

    # 6) 转换成 test 格式
    if exp.convert_to_test:
        test_json = case_dir / f"{case_name}_test.json"
        convert_benchmark_to_test(benchmark_json, test_json)

    # 7) 可选：再翻译成 Dask 工作流
    if exp.translate_to_dask:
        dask_out = case_dir / "dask"
        dask_out.mkdir(exist_ok=True)
        translator = DaskTranslator(benchmark_json)
        translator.translate(output_folder=dask_out)

    print(f"[OK] generated: {case_dir}")


def main():
    output_root = Path("./outputs")
    output_root.mkdir(exist_ok=True)

    experiments = load_experiments(Path("./experiments.json"))

    for exp in experiments:
        for i in range(exp.repeat):
            generate_one_case(exp, i, output_root)


if __name__ == "__main__":
    main()