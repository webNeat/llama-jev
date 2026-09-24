import json
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
  (output_dir / 'score.md').write_text(format_table(scores) + '\n', encoding='utf-8')
  print(format_terminal(scores))
  print(f'Results: {output_dir}')
  raise SystemExit(run_result.returncode)

def format_table(data):
  lines = [
    '| Dataset | Intelligence | Calibration | Speed | Score |',
    '| --- | --- | --- | --- | --- |',
  ]
  for tier, entry in data.items():
    lines.append('| ' + ' | '.join(score_cells(tier, entry)) + ' |')
  return '\n'.join(lines)

def format_terminal(data):
  header = ['Dataset', 'Intelligence', 'Calibration', 'Speed', 'Score']
  rows = [score_cells(tier, entry) for tier, entry in data.items()]
  widths = [max(len(row[i]) for row in [header] + rows) for i in range(len(header))]
  lines = []
  for row in [header, ['-' * width for width in widths]] + rows:
    lines.append('  '.join(cell.rjust(widths[i]) if i else cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
  return '\n'.join(lines)

def score_cells(tier, entry):
  return [tier] + ['null' if value is None else str(value) for value in entry.values()]

def score_results(results_path):
  from jevbench.composite_v13 import chance_corrected_accuracy, intelligence
  from jevbench.summarize import metric
  from jevbench.tasks import load_jsonl

  results = [json.loads(line) for line in results_path.open()]
  tier_tasks = {}
  for task_path in task_paths.split(','):
    stem = Path(task_path).stem
    tier_tasks[tier_names.get(stem, stem)] = load_jsonl(str(jevbench_dir / task_path))

  scored_tasks = {}
  for tier, tasks in tier_tasks.items():
    if tier == 'standard' and 'easy' in tier_tasks:
      scored_tasks['easy + standard'] = tier_tasks['easy'] + tasks
    else:
      scored_tasks[tier] = tasks

  scores = {}
  for tier, tasks in scored_tasks.items():
    metrics = metric(tasks, results)
    intel = chance_corrected_accuracy(metrics['accuracy'], guess_rate(tasks)) if metrics['accuracy'] is not None else None
    scores[tier] = score_axes(metrics, intel)

  global_metrics = metric([task for tasks in tier_tasks.values() for task in tasks], results)
  tier_chances = {tier: guess_rate(tasks) for tier, tasks in tier_tasks.items()}
  accuracies = {tier: metric(tasks, results)['accuracy'] for tier, tasks in tier_tasks.items()}
  global_intel = intelligence(accuracies, tier_chances)
  scores['global'] = score_axes(global_metrics, global_intel)
  return {tier: {k: round(v, 1) if isinstance(v, float) else v for k, v in entry.items()} for tier, entry in scores.items()}

def guess_rate(tasks):
  return sum(1 / len(task.labels) for task in tasks) / len(tasks)

def score_axes(metrics, intel):
  from jevbench.composite_v13 import calibration, speed

  cal = calibration(metrics['ece']['ece']) if metrics['ece'] else None
  spd = speed(metrics['latency']['p50_s'], metrics['latency']['p95_s'], endpoint_kind)
  return {'intelligence': intel, 'calibration': cal, 'speed': spd, 'score': combined_score(intel, cal, spd)}

def combined_score(intel, cal, spd):
  if intel is None or cal is None or spd is None:
    return None
  return (intel + cal + spd) / 3

main()
