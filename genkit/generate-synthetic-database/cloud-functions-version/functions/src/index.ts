// Copyright 2024 Google LLC
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// 
//    https://www.apache.org/licenses/LICENSE-2.0
// 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { onRequest} from "firebase-functions/v2/https";
import * as logger from "firebase-functions/logger";

// Import necessary modules for interacting with GenKit AI and data manipulation.
import { generate } from '@genkit-ai/ai';
import { configureGenkit } from '@genkit-ai/core';
import { defineFlow,runFlow } from '@genkit-ai/flow';
import { gemini15ProPreview, vertexAI } from '@genkit-ai/vertexai';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore, Timestamp } from 'firebase-admin/firestore';
import {v4 as uuidv4} from 'uuid';
import * as z from 'zod';

// Configure Genkit with Vertex AI plugin and logging settings.
configureGenkit({
  plugins: [
    vertexAI({ projectId: 'ai-startup-school-firebase', location: 'us-central1'}),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

// Define an Order object.
class Order {
  order_id: string;
  user_id: string;
  item: string;
  quantity: number;
  total_sales: number;
  status: string;
  created_at: Timestamp;
  shipped_at: Timestamp | null;
  delivered_at: Timestamp | null;
  age: number;
  gender: string;
  customer_rating: number;
  customer_review: string;
  
  constructor(
      order_id: string,
      user_id: string,
      item: string,
      quantity: number,
      total_sales: number,
      status: string,
      created_at: Timestamp,
      shipped_at: Timestamp | null,
      delivered_at: Timestamp | null,
      age: number,
      gender: string,
      customer_rating: number,
      customer_review: string,
  ) {
    this.order_id = order_id;
    this.user_id = user_id;
    this.item = item;
    this.quantity = quantity;
    this.total_sales = total_sales;
    this.status = status;
    this.created_at = created_at;
    this.shipped_at = shipped_at;
    this.delivered_at = delivered_at;
    this.age = age;
    this.gender = gender;
    this.customer_rating = customer_rating;
    this.customer_review = customer_review;
  }
}

// Generates a random integer between the specified minimum and maximum values (inclusive).
function getRandomIntInclusive(min: number, max: number): number {
  // Ensure the minimum is less than or equal to the maximum
  min = Math.ceil(min);
  max = Math.floor(max);

  // Generate a random number within the range
  return Math.floor(Math.random() * (max - min + 1)) + min; 
}
  
  
// Define dogfood menu item details to be used as input for the data generation.
const menuItems = [
  "Doggo chicken instant ramen is sold for $7.99.",
  "Doggo cheese burger is sold for $8.99.",
  "Doggo shrimp fried rice is sold for $8.99.",
  "Doggo pulled pork tacos is sold for $7.99.",
  "Doggo NY style pizza is sold for $6.99.",
  "Doggo Arepa is sold for $6.99."
]


// Define a Zod schema to validate the structure of Bone Appetit sales data.
const BoneAppetitSalesDatabaseSchema = z.object({
  item: z.string().describe('Name of the dog food item the customer has purchased.'),
  quantity: z.number().int().describe('Number of items the customer has purchased.'),
  total_sales: z.number().describe('Total cost of the items in the order.'),
  status: z.string().describe('Status of the order such as "Pending," "Processing," "Shipped," "Delivered," "Cancelled"'),
  created_at: z.string().describe('Date and time when the order was placed, NULL if not yet created. The date and time must be after the year 2022.'),
  shipped_at: z.string().describe('Date and time when the order was shipped, NULL if not yet shipped. The date and time must be after the year 2022.'),
  delivered_at: z.string().describe('Date and time when the order was delivered, NULL if not yet delivered. The date and time must be after the year 2022.'),
  gender: z.string().describe("Customer's gender. It can be either Female or Male."),
  customer_rating: z.number().describe('Rating given by the customer. Rating range is between 1 to 5.'),
  customer_review: z.string().describe('Authentic, insightful, fun, honest and unique review from a valued customer based on the given rating.'),
});

// Define a GenKit flow to create Bone Appetit sales data rows using the Gemini 1.5 Pro model.
const createBoneAppetitSalesRowSchema = defineFlow({
  name: "createBoneAppetitSalesRowSchema",
  inputSchema: z.string(),
  outputSchema: BoneAppetitSalesDatabaseSchema, // Ensure this schema is well-defined
}, async (input) => {
  const result = await generate({
    model: gemini15ProPreview,
    config: { temperature: 0.3, maxOutputTokens: 8192},
    prompt: `Generate one unique row of a dataset table at a time. Dataset description: This is a dog food sales database with reviews. Here is the item and its price: ${input}. The customer rating is: ${getRandomIntInclusive(0,5)}. Please ensure the customer review matches the given rating. If the rating is less than 3, please give an honest bad review.`,
    output: {format:'json', schema: BoneAppetitSalesDatabaseSchema }
  });

  // 1. Get the parsed result
  const BoneAppetitSaleRowItem = result.output();

  // 2. Handle the null case more effectively
  if (BoneAppetitSaleRowItem === null) {
    // Instead of a placeholder, throw an error to signal failure
    logger.error("Failed to generate a valid BoneAppetitSaleRowItem.");
    throw new Error("Failed to generate a valid BoneAppetitSaleRowItem.");
  }

  // 3. Return valid row data
  return BoneAppetitSaleRowItem; // This now aligns with the expected schema
});

// Interface defining the structure of the resolved response from the AI generation.
interface ResolvedResponse {
  item: string;
  quantity: number;
  total_sales: number;
  status: string;
  created_at: string;
  shipped_at: string;
  delivered_at: string;
  gender: string;
  customer_rating: number;
  customer_review: string;
}

// Rate-Limited Generator Function (yields Promises at a controlled rate).
function* rateLimitedRunFlowGenerator(
  maxRequestsPerMinute: number = 60
): Generator<Promise<ResolvedResponse>, void, unknown> {
  let startTime = Date.now();
  let requestsThisMinute = 0;

  while (true) {
    const elapsedTime = Date.now() - startTime;

    if (elapsedTime >= 60 * 1000) { // Reset counter every minute
      requestsThisMinute = 0;
      startTime = Date.now();
    }

    if (requestsThisMinute < maxRequestsPerMinute) {
      requestsThisMinute++;
      yield runFlow(createBoneAppetitSalesRowSchema, menuItems[getRandomIntInclusive(0, 5)]);
    } else {
      const timeToWait = 60 * 1000 - elapsedTime;
      yield new Promise((resolve) => setTimeout(resolve, timeToWait));
    }
  }
}

// Create a helper function for converting the Order object to plain object.
function orderToPlainObject(order: Order): Record<string, any> {
  return {
    order_id: order.order_id,
    user_id: order.user_id,
    item: order.item,
    quantity: order.quantity,
    total_sales: order.total_sales,
    status: order.status,
    created_at: order.created_at,
    shipped_at: order.shipped_at,
    delivered_at: order.delivered_at,
    age: order.age,
    gender: order.gender,
    customer_rating: order.customer_rating,
    customer_review: order.customer_review,
  };
}

// Define constant.
const app = initializeApp();
const BATCH_SIZE = 20;

// Create a Bone Appetit Sales Database and store it in Firestore document by document.
export const createBoneAppetitSalesDatabase = onRequest(
  async (request, response) => { 
  try {
    const generator = rateLimitedRunFlowGenerator(); // Create the generator
    const db = getFirestore(app); 
    const collectionRef = db.collection("BoneAppetitSales");
    let batch = db.batch();
    let batchCount = 0;
    let i = 0;
    while (i<=200){
      try{
        const responsePromise = generator.next().value; // Get the next Promise from the generator
        const structuredResponse = await responsePromise; 
        if (structuredResponse) {
          const orderObj = new Order(
            uuidv4(),
            uuidv4(),
            structuredResponse["item"],
            structuredResponse["quantity"],
            structuredResponse["total_sales"],
            structuredResponse["status"],
            Timestamp.fromDate(new Date(structuredResponse["created_at"])),
            Timestamp.fromDate(new Date(structuredResponse["shipped_at"])),
            Timestamp.fromDate(new Date(structuredResponse["delivered_at"])),
            getRandomIntInclusive(21, 53),
            structuredResponse["gender"],
            structuredResponse["customer_rating"],
            structuredResponse["customer_review"],
          );
          const orderData = orderToPlainObject(orderObj);
          logger.log("This is the current order: " + orderObj.order_id);
          const orderRef = collectionRef.doc(orderObj.order_id);
          batch.set(orderRef, orderData);
          batchCount++;
          logger.log("Successfully added Order: " + orderObj.order_id + " to Batch.");
          // If batch size limit is reached, commit the batch and start a new one.
          if (batchCount >= BATCH_SIZE) {
              await batch.commit(); // Commit the batch
              logger.log("Successfully commited a full batch of orders to Firestore.");
              batch = db.batch();     // Create a new batch
              batchCount = 0; 
          }
          i++;
        }
      }catch (error) {
        logger.error(`Error in runFlow for iteration ${i}: ${error}`);
        // Enhanced error handling with error message
      }
    } 
    // Commit any remaining orders in the last batch.
    if (batchCount>0){
      await batch.commit();
    }
  }
    catch (error) {
    logger.error("Error generating Order Object:", error);
  }
});