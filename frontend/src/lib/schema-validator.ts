/** Zod schemas for frontend validation. */

import { z } from "zod";

export const generateRequestSchema = z.object({
  prompt: z
    .string()
    .min(3, "Prompt must be at least 3 characters")
    .max(5000, "Prompt must be under 5000 characters"),
  options: z
    .object({
      skip_codegen: z.boolean().optional().default(false),
      fast_mode: z.boolean().optional().default(false),
    })
    .optional()
    .default({}),
});

export type GenerateRequestInput = z.infer<typeof generateRequestSchema>;

export const evaluateRequestSchema = z.object({
  prompt_ids: z.array(z.string()).optional().default([]),
});

export type EvaluateRequestInput = z.infer<typeof evaluateRequestSchema>;
