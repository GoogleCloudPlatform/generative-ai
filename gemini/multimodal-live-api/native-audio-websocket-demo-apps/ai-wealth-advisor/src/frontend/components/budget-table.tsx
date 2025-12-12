// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// import React from "react"
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

// export interface Budget {
//   title: string
//   income: {
//     label: string
//     value: number
//   }
//   expenses: {
//     label: string
//     value: number
//   }[]
//   summary: {
//     label: string
//     value: number
//     savings_label: string
//     savings_value: number
//   }
// }

// interface BudgetTableProps {
//   budget: Budget
// }

// export const BudgetTable: React.FC<BudgetTableProps> = ({ budget }) => {
//   return (
//     <Card className="w-full max-w-2xl mx-auto my-4">
//       <CardHeader>
//         <CardTitle>{budget.title}</CardTitle>
//       </CardHeader>
//       <CardContent>
//         <div className="grid gap-4">
//           <div className="flex justify-between items-center border-b pb-2">
//             <span className="font-semibold">{budget.income.label}</span>
//             <span className="text-green-600">${budget.income.value.toLocaleString()}</span>
//           </div>
//           <div>
//             <h4 className="font-semibold mb-2">Expenses</h4>
//             {budget.expenses.map((expense, index) => (
//               <div key={index} className="flex justify-between items-center mb-1">
//                 <span>{expense.label}</span>
//                 <span>-${expense.value.toLocaleString()}</span>
//               </div>
//             ))}
//           </div>
//           <div className="flex justify-between items-center border-t pt-2">
//             <span className="font-semibold">{budget.summary.label}</span>
//             <span className="font-bold">-${budget.summary.value.toLocaleString()}</span>
//           </div>
//           <div className="flex justify-between items-center border-t pt-2 mt-2">
//             <span className="font-semibold">{budget.summary.savings_label}</span>
//             <span className="font-bold text-green-600">${budget.summary.savings_value.toLocaleString()}</span>
//           </div>
//         </div>
//       </CardContent>
//     </Card>
//   )
// }
