import json
import math
import subprocess
import sys
from pathlib import Path
from datetime import datetime

root_dir = Path(__file__).resolve().parent
jevbench_dir = root_dir / 'bench' / 'jevbench'
endpoint_url = 'http://localhost:3000'
model_name = 'llama-jev'
task_paths = 'datasets/public/easy.jsonl,datasets/public/original.jsonl,datasets/public/hard.jsonl'
tier_names = {'easy': 'easy', 'original': 'standard', 'hard': 'hard'}
endpoint_kind = 'gpu'

def main():
  if not jevbench_dir.is_dir():
    subprocess.run(['git', 'clone', 'https://github.com/fstandhartinger/jevbench', str(jevbench_dir)], check=True)

  output_dir = root_dir / 'bench' / datetime.now().strftime('run-%Y-%m-%d-%H-%M-%S-%f')
  output_dir.mkdir(parents=True)
  results_path = output_dir / 'results.jsonl'
  ledger_path = output_dir / 'ledger.jsonl'

  run_result = subprocess.run([
    sys.executable, '-m', 'jevbench.cli', 'run',
    '--tasks', task_paths,
    '--adapter', 'typesafe',
    '--endpoint', endpoint_url,
    '--model', model_name,
    '--key-env', '',
    '--cost-basis', 'local_gpu_no_provider_tariff',
    '--reserve-usd', '0',
    '--results', str(results_path),
    '--raw-dir', str(output_dir / 'raw'),
    '--ledger', str(ledger_path),
    '--manifest', str(output_dir / 'manifest.json'),
  ], cwd=jevbench_dir)

  if not results_path.exists():
    raise SystemExit(run_result.returncode or 'Benchmark produced no results')

  summary_result = subprocess.run([
    sys.executable, '-m', 'jevbench.cli', 'summarize',
    '--tasks', task_paths,
    '--results', str(results_path),
    '--ledger', str(ledger_path),
  ], cwd=jevbench_dir, check=True, stdout=subprocess.PIPE, text=True)
  (output_dir / 'summary.json').write_text(summary_result.stdout, encoding='utf-8')

  sys.path.insert(0, str(jevbench_dir))
  scores = score_results(results_path)
  scores_yaml = format_yaml(scores)
  (output_dir / 'score.yaml').write_text(scores_yaml + '\n', encoding='utf-8')
  print(scores_yaml)
  print(f'Results: {output_dir}')
  raise SystemExit(run_result.returncode)

def format_yaml(data):
  lines = []
  for tier, entry in data.items():
    lines.append(f'{tier}:')
    for key, value in entry.items():
      lines.append(f'  {key}: {"null" if value is None else value}')
  return '\n'.join(lines)

def score_results(results_path):
  from jevbench.composite_v13 import chance_corrected_accuracy, intelligence
  from jevbench.summarize import metric
  from jevbench.tasks import load_jsonl

  results = [json.loads(line) for line in results_path.open()]
  tier_tasks = {}
  for task_path in task_paths.split(','):
    stem = Path(task_path).stem
    tier_tasks[tier_names.get(stem, stem)] = load_jsonl(str(jevbench_dir / task_path))

  tier_metrics = {tier: metric(tasks, results) for tier, tasks in tier_tasks.items()}
  tier_chances = {tier: sum(1 / len(task.labels) for task in tasks) / len(tasks) for tier, tasks in tier_tasks.items()}
  scores = {}
  for tier, metrics in tier_metrics.items():
    intel = chance_corrected_accuracy(metrics['accuracy'], tier_chances[tier]) if metrics['accuracy'] is not None else None
    scores[tier] = score_axes(metrics, intel)

  global_metrics = metric([task for tasks in tier_tasks.values() for task in tasks], results)
  accuracies = {tier: metrics['accuracy'] for tier, metrics in tier_metrics.items() if metrics['accuracy'] is not None}
  global_intel = intelligence(accuracies, tier_chances)
  scores['global'] = score_axes(global_metrics, global_intel)
  return {tier: {k: round(v, 1) if isinstance(v, float) else v for k, v in entry.items()} for tier, entry in scores.items()}

def score_axes(metrics, intel):
  from jevbench.composite_v13 import calibration, speed

  cal = calibration(metrics['ece']['ece']) if metrics['ece'] else None
  spd = speed(metrics['latency']['p50_s'], metrics['latency']['p95_s'], endpoint_kind)
  return {'intelligence': intel, 'calibration': cal, 'speed': spd, 'score': combined_score(intel, cal, spd)}

def combined_score(intel, cal, spd):
  from jevbench.composite_v13 import near_chance_multiplier

  values = [max(v, 1.0) for v in (intel, cal, spd) if v is not None]
  if not values:
    return None
  return math.exp(sum(math.log(v) for v in values) / len(values)) * near_chance_multiplier(intel)

main()
