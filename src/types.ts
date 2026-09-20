export type Request = {
  state: string
  model: string
  questions: Record<string, Question>
}

export type Response = {
  model: string
  answers: Record<string, Answer>
}

export type Question = {
  type: 'choice'
  instructions: string
  criteria: Record<string, string | null>
}

export type Answer = {
  type: 'choice'
  choice: string
  probabilities: Record<string, number>
  confidence: number
}
