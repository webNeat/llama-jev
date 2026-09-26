import { ChoiceAnswer, ChoiceQuestion, NoulAnswer, NoulQuestion, Question, Request, Response, ScoreAnswer, ScoreQuestion } from './types.js'

const samples = {
  noul: [
    {
      role: 'user',
      content: user_prompt('The office is open on Mondays.', 'Is the office open on Mondays?', [
        'Yes: The office is open',
        'No: The office is closed',
      ]),
    },
    { role: 'assistant', content: '1' },
    {
      role: 'user',
      content: user_prompt('The office is closed on Sundays.', 'Is the office open on Sundays?', [
        'Yes: The office is open',
        'No: The office is closed',
      ]),
    },
    { role: 'assistant', content: '2' },
  ],
  score: [
    {
      role: 'user',
      content: user_prompt('The customer says the service was awful.', 'Rate the service.', [
        'Very poor',
        'Poor',
        'Good',
        'Excellent',
        'I am not sure',
      ]),
    },
    { role: 'assistant', content: '1' },
    {
      role: 'user',
      content: user_prompt('The customer says the service was excellent.', 'Rate the service.', [
        'Very poor',
        'Poor',
        'Good',
        'Excellent',
        'I am not sure',
      ]),
    },
    { role: 'assistant', content: '4' },
  ],
  choice: [
    {
      role: 'user',
      content: user_prompt('The customer was charged twice for one purchase.', 'Which team should handle this?', [
        'Sales: Pricing questions',
        'Billing: Charges and refunds',
        'Technical: Bugs and errors',
        'I am not sure',
      ]),
    },
    { role: 'assistant', content: '2' },
    {
      role: 'user',
      content: user_prompt('Please translate this document into French.', 'Which task is requested?', [
        'Summarize',
        'Proofread',
        'Translate',
        'I am not sure',
      ]),
    },
    { role: 'assistant', content: '3' },
  ],
}

export async function jev({ model, state, questions }: Request): Promise<Response> {
  const entries = Object.entries(questions)
  const results = await Promise.all(entries.map(([_, question]) => answer(state, question)))
  const res: Response = { model, answers: {}, usage: { input_tokens: 0, output_tokens: 0 } }
  for (let i = 0; i < entries.length; i++) {
    const [name] = entries[i]!
    res.answers[name] = results[i]!
  }
  return res
}

async function answer(state: unknown, question: Question) {
  if (question.type === 'noul') return noul_answer(state, question)
  if (question.type === 'score') return score_answer(state, question)
  if (question.type === 'choice') return choice_answer(state, question)
}

async function choice_answer(state: unknown, question: ChoiceQuestion): Promise<ChoiceAnswer> {
  const choices = Object.keys(question.criteria)
  const options = choices.map((choice) => choice + (question.criteria[choice] ? ': ' + to_str(question.criteria[choice]) : ''))
  options.push(`I am not sure`)
  const probs = await classify('choice', to_str(state), to_str(question.instructions), options)
  const uncertainty = probs.pop()!
  const probs_total = probs.reduce((a, b) => a + b, 0)
  let top_choice_index = 0
  const probabilities: Record<string, number> = {}
  for (let i = 0; i < choices.length; i++) {
    probabilities[choices[i]] = probs[i] / probs_total
    if (probs[i] > probs[top_choice_index]) top_choice_index = i
  }
  return {
    type: 'choice',
    choice: choices[top_choice_index],
    probabilities,
    confidence: 1 - uncertainty,
  }
}

async function noul_answer(state: unknown, question: NoulQuestion): Promise<NoulAnswer> {
  const probs = await classify('noul', to_str(state), to_str(question.instructions), [
    'Yes' + (question.criteria?.true ? ': ' + to_str(question.criteria?.true) : ''),
    'No' + (question.criteria?.false ? ': ' + to_str(question.criteria?.false) : ''),
  ])
  return {
    type: 'noul',
    noul: probs[0] / (probs[0] + probs[1]),
  }
}

async function score_answer(state: unknown, question: ScoreQuestion): Promise<ScoreAnswer> {
  const options = question.criteria.map((choice) => to_str(choice))
  options.push(`I am not sure`)
  const probs = await classify('score', to_str(state), to_str(question.instructions), options)
  const uncertainty = probs.pop()!
  const probs_total = probs.reduce((a, b) => a + b, 0)
  let score = 0
  const probabilities: Record<string, number> = {}
  const legend: Record<string, unknown> = {}
  for (let i = 0; i < question.criteria.length; i++) {
    legend[i] = question.criteria[i]
    probabilities[i] = probs[i] / probs_total
    score += (i * probs[i]) / probs_total
  }
  return {
    type: 'score',
    score,
    legend,
    probabilities,
    confidence: 1 - uncertainty,
  }
}

async function classify(type: Question['type'], state: string, instructions: string, options: string[]) {
  const res = await fetch('http://localhost:8080/apply-template', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: [
        { role: 'system', content: 'Output the number of the correct choice.' },
        ...samples[type],
        { role: 'user', content: user_prompt(state, instructions, options) },
      ],
      chat_template_kwargs: { enable_thinking: false },
    }),
  })
  const data: any = await res.json()
  const next_tokens = options.map((_, i) => String(i + 1))
  const probs = await next_token_probs(data.prompt, next_tokens)
  return options.map((_, i) => probs[i + 1] ?? 0)
}

async function next_token_probs(prompt: string, tokens: string[]) {
  const grammar = `root ::= ${tokens.map((x) => `"${x}"`).join('|')}`
  const res = await fetch('http://localhost:8080/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, n_predict: 1, n_probs: 10 * tokens.length, grammar }),
  })
  const data: any = await res.json()
  const probs: Record<string, number> = {}
  for (const { token, logprob } of data.completion_probabilities[0].top_logprobs) {
    const key = token.trim()
    if (tokens.includes(key)) {
      if (probs[key] === undefined) probs[key] = 0
      probs[key] += Math.exp(logprob)
    }
  }
  return probs
}

function user_prompt(state: string, instructions: string, options: string[]) {
  const prompt = [state, `\n---\n`, `Question: ${instructions}\n`, `Choices:`]
  const next_tokens: string[] = []
  for (let i = 1; i <= options.length; i++) {
    prompt.push(`  ${i}. ${options[i - 1]}`)
    next_tokens.push(String(i))
  }
  return prompt.join(`\n`)
}

function to_str(data: unknown) {
  if (typeof data === 'string') return data
  return JSON.stringify(data)
}
