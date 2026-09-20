async function next_token_probs(prompt: string, n_probs: number) {
  const res = await fetch('http://localhost:8080/completion', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, n_predict: 1, n_probs }),
  })
  const data: any = await res.json()
  const probs: Record<string, number> = {}
  for (const { token, logprob } of data.completion_probabilities[0].top_logprobs) {
    probs[token] = Math.exp(logprob)
  }
  return probs
}

type Question = {
  instructions: string
  choices: Record<string, string>
}
type Answer = {
  probabilities: Record<string, number | undefined>
  confidence: number
}
async function jev_answer(state: string, question: Question) {
  question.choices['not sure'] = 'I am not confident'
  const prompt = [state, `\n---\n`, `Question: ${question.instructions}\n`, `Choices:`]
  const choices = Object.entries(question.choices)
  let n = 1
  for (const [choice, description] of choices) {
    prompt.push(`  ${n}. ${choice}: ${description}`)
    n += 1
  }
  prompt.push(`\nNumber of the correct choice: `)
  const probs = await next_token_probs(prompt.join(`\n`), 10)
  const answer: Answer = {
    probabilities: {},
    confidence: 0,
  }
  let total_probs = 0
  for (let i = 0; i < choices.length; i++) {
    const n = i + 1
    const [choice] = choices[i]!
    if (choice === 'not sure') answer.confidence = 1 - probs[n]!
    else {
      answer.probabilities[choice] = probs[n]
      total_probs += probs[n]!
    }
  }
  for (const name of Object.keys(answer.probabilities)) {
    answer.probabilities[name]! /= total_probs
  }
  return answer
}

async function jev(state: string, questions: Record<string, Question>) {
  const entries = Object.entries(questions)
  const results = await Promise.all(entries.map(([_, question]) => jev_answer(state, question)))
  const answers: Record<string, Answer> = {}
  for (let i = 0; i < entries.length; i++) {
    const [name] = entries[i]!
    answers[name] = results[i]!
  }
  return answers
}

const state =
  "Our API integration started returning 500 errors on every request about 20 minutes ago, and we can't process any customer orders until this is fixed."

const start = performance.now()
const res = await jev(state, {
  department: {
    instructions: 'Which team should handle this',
    choices: {
      billing: 'Payment or subscription issues',
      technical: 'Bugs or integration problems',
      sales: 'Pricing or account questions',
    },
  },
  is_urgent: {
    instructions: 'The message conveys urgency or time-sensitivity',
    choices: { yes: '', no: '' },
  },
})
const duration = Math.floor(performance.now() - start)

console.log(duration)
console.log(JSON.stringify(res, null, 2))
