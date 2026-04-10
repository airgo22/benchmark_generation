import argparse 
from pathlib import Path
import json
import ast
import random

tasks = []

def parse_arguments():
    parser = argparse.ArgumentParser(description="Convert wfcommons benchmark JSON to ours.")
    parser.add_argument("--input", "-i", type=str, required=True, help="wfcommons benchmark JSON file")
    parser.add_argument("--output", "-o", type=str, required=True, help="adapted json file for ours")
    parser.add_argument("--namespace", "-n", type=str, default="test", help="namespace (default: test)")
    parser.add_argument("--task_name", "-w", type=str, default=None, help="task name (optional)")
    return parser.parse_args()

def get_tasks_dag(benchmark_tasks):
    task = tasks[-1] 

    group_name = benchmark_tasks.get("id" , "") 
    if group_name == "" :
        print("[error] a group without id , check it!")
    # print("group_name : " , group_name)

    group_parents = benchmark_tasks.get("parents" , []) 
    # print(group_parents)

    task["spec"]["groups"].append(
        {
            "name" : group_name ,
            "parents" : group_parents ,
            "actions" : [{
                "name" : "A1" ,
                "runtimes" : []
                }]
        }
    )
    # print("task :" , task)
    tasks[-1] = task 

def get_runtimes(runtime):
    arguments = runtime["command"]["arguments"] 
    dataSpec = []
    output = [] 
    args = []
    conditions = {
        "formulas": [{
            "condition_type":"DataDependency",
            "left_value" : {
                "type" : "file" 
            },
            "right_value" : {}
        }]
    }
    for item in arguments:
        parts = item.split(" ", 1)
        if len(parts) == 1:
            args.append(parts[0])
            continue

        flag, value = parts[0], parts[1]

        # 针对 output-files / input-files 做特殊处理：Python -> JSON
        if flag in ("--output-files", "--input-files"):
            try:
                # 先把 "{'a': 1, 'b': 2}" / "['x', 'y']" 解析成Python对象
                py_obj = ast.literal_eval(value)
                json_str = json.dumps(py_obj)
                if flag == "--input-files":
                    download_files = json.loads(json_str)
                    for fp in download_files:   
                        dataSpec.append({
                            "name": fp,
                            "fileFormat": "file",
                        })
                if flag == "--output-files":
                    upload_files = json.loads(json_str)
                    for uf in upload_files:   
                        output.append({
                            "name": uf,
                            "type": "file",
                        })
                args.extend([flag, json_str])
            except Exception:
                # 解析失败
                args.extend([flag, value])
        else:
            # 直接拆开
            args.extend([flag, value])
        
            # 如果缺少 CPU 参数，则对特定任务类型自动补齐

    # TODO : 这里可以根据不同的任务类型，补齐不同的资源参数，目前先针对 bowtie2 做了补齐    
    # 如果缺少 CPU 参数，则自动补齐
    arg_flags = set(args[::2])  # 取出所有 flag，例如 --name, --output-files ...

    if "--percent-cpu" not in arg_flags:
        random_cpu_percent = round(random.uniform(0.5, 0.9), 2)  # 生成一个随机数，模拟不同任务的 CPU 占用率
        args.extend(["--percent-cpu", str(random_cpu_percent)])

    if "--cpu-work" not in arg_flags:
        random_cpu_work = random.randint(1000, 5000)  # 生成一个随机数，模拟不同任务的 CPU 工作量
        args.extend(["--cpu-work", str(random_cpu_work)])


    if dataSpec != [] :
        rt = {
            "name" : "R1" ,
            "type" : "command" , 
            "command" : [runtime["command"]["program"]] , 
            "args" : args ,
            "data" : dataSpec,
            "outputs" : output,
            "conditions" : conditions
            }
    else :
         rt = {
            "name" : "R1" ,
            "type" : "command" , 
            "command" : [runtime["command"]["program"]] , 
            "args" : args ,
            "data" : dataSpec,
            "outputs" : output
            }

    
    # TODO :  内存资源
    cpu_lowbound = int(runtime.get("coreCount" , 0))
    cpu_upperbound = cpu_lowbound + 2 
    cpu_req = {
        "name" : "CPU" ,
        "lowbound" : str(cpu_lowbound) ,
        "upperbound" : str(cpu_upperbound) 
        }
    

    task = tasks[-1] 
    groups = task["spec"]["groups"] 
    for idx , group in enumerate(groups) :
        if group["name"] == runtime["id"] :
            groups[idx]["actions"][0]["runtimes"].append(rt)
            resource_requirements = groups[idx].get("resource_requirements" , [])
            resource_requirements.append(cpu_req)
            groups[idx]["resource_requirements"] = resource_requirements

    tasks[-1]["spec"]["groups"] = groups


def main():
    # 解析参数
    arg = parse_arguments()
    input_path = Path(arg.input)
    output_path = Path(arg.output)
    print("input path:", input_path)
    print("output path:", output_path)

    # 获取原始json文件
    with input_path.open("r", encoding="utf-8") as f:
        benchmark = json.load(f)
    
    # 获取任务名称
    task_name = (
        arg.task_name
        or
        benchmark.get("name" , "default_task")
    )
    task_namespace = (
        arg.namespace 
        or 
        "test" 
    )
    print(f"task name:{task_name} , task namespace : {task_namespace}")

    # 构建task
    task = {
        "kind" : "Task" ,
        "namespace": task_namespace ,
        "spec" : {
            "name" : task_name ,
            "groups" : [] 
        }
    }
    tasks.append(task)

    # 获取groups
    groups = benchmark.get("workflow", {}).get("specification" , {}).get("tasks" , [])
    print("groups nums:", groups.__len__())


    # TODO: 这里想想能咋优化，可以先把parents存成字典，后面需要的话改吧 task['id'] = parents 
    # 转换groups
    for group in groups:
        get_tasks_dag(group)

    # 添加runtimes
    runtimes = benchmark.get("workflow", {}).get("execution" , {}).get("tasks" , [])
    for runtime in runtimes:
        get_runtimes(runtime)


    with open(output_path , "w") as f :
        for task in tasks :
            json_str = json.dumps(task, ensure_ascii=False, indent=2)
            f.write(json_str)
    # print(tasks)



if __name__ == "__main__":
    main() 