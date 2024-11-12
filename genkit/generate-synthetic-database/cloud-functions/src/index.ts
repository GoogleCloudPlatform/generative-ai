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

import { onRequest } from "firebase-functions/v2/https";
import * as logger from "firebase-functions/logger";

// Import necessary modules for interacting with GenKit AI and data manipulation.
import { generate } from "@genkit-ai/ai";
import { configureGenkit } from "@genkit-ai/core";
import { defineFlow, runFlow } from "@genkit-ai/flow";
import { gemini15ProPreview, vertexAI } from "@genkit-ai/vertexai";
import { initializeApp } from "firebase-admin/app";
import { getFirestore, Timestamp } from "firebase-admin/firestore";
import { v4 as uuidv4 } from "uuid";
import * as z from "zod";

// Configure Genkit with Vertex AI plugin and logging settings.
configureGenkit({
  plugins: [
    vertexAI({ projectId: "YOUR_PROJECT_ID", location: "LOCATION_ID" }),
  ],
  logLevel: "debug",
  enableTracingAndMetrics: true,
});

// Define an Order object.
class Order {
  orderId: string;
  userId: string;
  item: string;
  quantity: number;
  totalSales: number;
  status: string;
  createdAt: Timestamp;
  shippedAt: Timestamp | null;
  deliveredAt: Timestamp | null;
  age: number;
  gender: string;
  customerRating: number;
  customerReview: string;

  constructor(
    orderId: string,
    userId: string,
    item: string,
    quantity: number,
    totalSales: number,
    status: string,
    createdAt: Timestamp,
    shippedAt: Timestamp | null,
    deliveredAt: Timestamp | null,
    age: number,
    gender: string,
    customerRating: number,
    customerReview: string,
  ) {
    this.orderId = orderId;
    this.userId = userId;
    this.item = item;
    this.quantity = quantity;
    this.totalSales = totalSales;
    this.status = status;
    this.createdAt = createdAt;
    this.shippedAt = shippedAt;
    this.deliveredAt = deliveredAt;
    this.age = age;
    this.gender = gender;
    this.customerRating = customerRating;
    this.customerReview = customerReview;
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

// Define dog food menu item details to be used as input for the data generation.
const menuItems = [
  "Doggo chicken instant ramen is sold for $7.99.",
  "Doggo cheese burger is sold for $8.99.",
  "Doggo shrimp fried rice is sold for $8.99.",
  "Doggo pulled pork tacos is sold for $7.99.",
  "Doggo NY style pizza is sold for $6.99.",
  "Doggo Arepa is sold for $6.99.",
];

// Define a Zod schema to validate the structure of Bone Appetit sales data.
const boneAppetitSalesDatabaseSchema = z.object({
  item: z
    .string()
    .describe("Name of the dog food item the customer has purchased."),
  quantity: z
    .number()
    .int()
    .describe("Number of items the customer has purchased."),
  totalSales: z.number().describe("Total cost of the items in the order."),
  status: z
    .string()
    .describe(
      'Status of the order such as "Pending," "Processing," "Shipped," "Delivered," "Cancelled"',
    ),
  createdAt: z
    .string()
    .describe(
      "Date and time when the order was placed, NULL if not yet created. The date and time must be after the year 2022.",
    ),
  shippedAt: z
    .string()
    .describe(
      "Date and time when the order was shipped, NULL if not yet shipped. The date and time must be after the year 2022.",
    ),
  deliveredAt: z
    .string()
    .describe(
      "Date and time when the order was delivered, NULL if not yet delivered. The date and time must be after the year 2022.",
    ),
  gender: z
    .string()
    .describe("Customer's gender. It can be either Female or Male."),
  customerRating: z
    .number()
    .describe("Rating given by the customer. Rating range is between 1 to 5."),
  customerReview: z
    .string()
    .describe(
      "Authentic, insightful, fun, honest and unique review from a valued customer based on the given rating.",
    ),
});

// Define a GenKit flow to create Bone Appetit sales data rows using the Gemini 1.5 Pro model.
const createBoneAppetitSalesRowSchema = defineFlow(
  {
    name: "createBoneAppetitSalesRowSchema",
    inputSchema: z.string(),
    outputSchema: boneAppetitSalesDatabaseSchema, // Ensure this schema is well-defined
  },
  async (input) => {
    const result = await generate({
      model: gemini15ProPreview,
      config: { temperature: 0.3, maxOutputTokens: 8192 },
      prompt: `Generate one unique row of a dataset table at a time. Dataset description: This is a dog food sales database with reviews. Here is the item and its price: ${input}. The customer rating is: ${getRandomIntInclusive(
        0,
        5,
      )}. Please ensure the customer review matches the given rating. If the rating is less than 3, please give an honest bad review.`,
      output: { format: "json", schema: boneAppetitSalesDatabaseSchema },
    });

    // 1. Get the parsed result
    const boneAppetitSaleRowItem = result.output();

    // 2. Handle the null case more effectively
    if (boneAppetitSaleRowItem === null) {
      // Instead of a placeholder, throw an error to signal failure
      logger.error("Failed to generate a valid BoneAppetitSaleRowItem.");
      throw new Error("Failed to generate a valid BoneAppetitSaleRowItem.");
    }

    // 3. Return valid row data
    return boneAppetitSaleRowItem; // This now aligns with the expected schema
  },
);

// Interface defining the structure of the resolved response from the AI generation.
interface ResolvedResponse {
  item: string;
  quantity: number;
  totalSales: number;
  status: string;
  createdAt: string;
  shippedAt: string;
  deliveredAt: string;
  gender: string;
  customerRating: number;
  customerReview: string;
}

// Rate-Limited Generator Function (yields Promises at a controlled rate).
function* rateLimitedRunFlowGenerator(
  maxRequestsPerMinute: number = 60,
): Generator<Promise<ResolvedResponse>, void, unknown> {
  let startTime = Date.now();
  let requestsThisMinute = 0;

  while (true) {
    const elapsedTime = Date.now() - startTime;

    if (elapsedTime >= 60 * 1000) {
      // Reset counter every minute
      requestsThisMinute = 0;
      startTime = Date.now();
    }

    if (requestsThisMinute < maxRequestsPerMinute) {
      requestsThisMinute++;
      yield runFlow(
        createBoneAppetitSalesRowSchema,
        menuItems[getRandomIntInclusive(0, 5)],
      );
    } else {
      const timeToWait = 60 * 1000 - elapsedTime;
      yield new Promise((resolve) => setTimeout(resolve, timeToWait));
    }
  }
}

// Create a helper function for converting the Order object to plain object.
function orderToPlainObject(order: Order): Record<string, any> {
  return {
    orderId: order.orderId,
    userId: order.userId,
    item: order.item,
    quantity: order.quantity,
    totalSales: order.totalSales,
    status: order.status,
    createdAt: order.createdAt,
    shippedAt: order.shippedAt,
    deliveredAt: order.deliveredAt,
    age: order.age,
    gender: order.gender,
    customerRating: order.customerRating,
    customerReview: order.customerReview,
  };
}

// Define constant.
const app = initializeApp();
const BATCH_SIZE = 20;

// Create a Bone Appetit Sales Database and store it in Firestore document by document.
export const createBoneAppetitSalesDatabase = onRequest(
  async (request, response) => {
    const generator = rateLimitedRunFlowGenerator(); // Create the generator
    const db = getFirestore(app);
    const collectionRef = db.collection("BoneAppetitSales");
    let batch = db.batch();
    let batchCount = 0;
    for (let i = 0; i < 200; i++) {
      const responsePromise = generator.next().value; // Get the next Promise from the generator
      const structuredResponse = await responsePromise;
      if (!structuredResponse) {
        throw new Error(`Error in runFlow for iteration ${i}`);
      }
      const orderObj = new Order(
        uuidv4(),
        uuidv4(),
        structuredResponse["item"],
        structuredResponse["quantity"],
        structuredResponse["totalSales"],
        structuredResponse["status"],
        Timestamp.fromDate(new Date(structuredResponse["createdAt"])),
        Timestamp.fromDate(new Date(structuredResponse["shippedAt"])),
        Timestamp.fromDate(new Date(structuredResponse["deliveredAt"])),
        getRandomIntInclusive(21, 53),
        structuredResponse["gender"],
        structuredResponse["customerRating"],
        structuredResponse["customerReview"],
      );
      const orderData = orderToPlainObject(orderObj);
      logger.log("This is the current order: " + orderObj.orderId);
      const orderRef = collectionRef.doc(orderObj.orderId);
      batch.set(orderRef, orderData);
      batchCount++;
      logger.log(
        "Successfully added Order: " + orderObj.orderId + " to Batch.",
      );
      // If batch size limit is reached, commit the batch and start a new one.
      if (batchCount >= BATCH_SIZE) {
        await batch.commit(); // Commit the batch
        logger.log(
          "Successfully committed a full batch of orders to Firestore.",
        );
        batch = db.batch(); // Create a new batch
        batchCount = 0;
      }
    }
    // Commit any remaining orders in the last batch.
    if (batchCount > 0) {
      await batch.commit();
    }
  },
);
