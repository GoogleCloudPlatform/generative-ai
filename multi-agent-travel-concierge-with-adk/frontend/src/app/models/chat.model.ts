export type CreateChatRequest = {
    text: string,
    chat_id?: string
}

export type Chat = {
    id: string,
    question: string,
    answer: string,
    intent: string,
    suggested_questions: string[],
}

export type DialogQuestion = {
    questionId: string,
    questionText: string,
    hasChip: boolean,
    options: string[],
    questionSequence: string,
    answer: string
}
