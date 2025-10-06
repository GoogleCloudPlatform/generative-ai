/*
####################################################################################
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
####################################################################################
*/


-- DESCRIPTION: Example PostgreSQL function to dynamically build a RAG-enriched 
--              prompt and invoke an LLM. 
-- DISCLAIMER:  This function is provided for demonstration purposes only and
--              should not be used in production without sufficient testing.
-- EXAMPLE USAGE:  SELECT * FROM llm(prompt => 'This is a simple prompt.');
DROP FUNCTION IF EXISTS llm;
CREATE FUNCTION llm(
    set_debug BOOLEAN DEFAULT false,
    enable_history BOOLEAN DEFAULT false,
    enable_stock_lookup BOOLEAN DEFAULT false,
    uid INT DEFAULT 2147483647,
    model TEXT DEFAULT 'gemini',
    user_role TEXT DEFAULT 'I am a generic user',
    llm_role TEXT DEFAULT ' You are a helpful AI Assistant',
    mission TEXT DEFAULT null,
    additional_context TEXT DEFAULT null,
    output_format TEXT DEFAULT null,
    examples TEXT DEFAULT null,
    prompt TEXT DEFAULT 'Tell me I need to pass in a prompt parameter.',
    output_instructions TEXT DEFAULT null,
    response_restrictions TEXT DEFAULT 'You have no response restrictions for this prompt.',
    disclaimer TEXT DEFAULT null,
    max_output_tokens INT DEFAULT 512,
    temperature DECIMAL DEFAULT 0.0,
    top_p DECIMAL DEFAULT 0.95,
    top_k DECIMAL DEFAULT 40
)
RETURNS TABLE (
    llm_prompt TEXT,
    llm_prompt_len INT,
    llm_response TEXT,
    llm_response_len INT,
    extractive_prompt TEXT,
    extractive_response TEXT,
    recommended_tickers TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    llm_prompt TEXT := '';
    llm_prompt_len INT := null;
    llm_response TEXT := null;
    interaction_history_count INT := 0;
    extractive_prompt TEXT := '';
    extractive_response TEXT := '';
    recommended_tickers TEXT := '';
BEGIN
    -- Define user and AI roles
    IF llm_role IS NOT null THEN SELECT CONCAT(llm_prompt, 'AI ROLE: ', llm_role, E'.\n') INTO llm_prompt; END IF;
    IF mission IS NOT null THEN SELECT CONCAT(llm_prompt, 'AI MISSION: ', mission, E'.\n') INTO llm_prompt; END IF;
    IF user_role IS NOT null THEN SELECT CONCAT(llm_prompt, 'USER ROLE: ', user_role, E' \n\n') INTO llm_prompt; END IF;
    
    -- Define the task/prompt
    IF prompt IS NOT null THEN SELECT CONCAT(llm_prompt, E'INSTRUCTIONS: \n- Respond to the PROMPT using FEWER than ', CAST (ROUND(max_output_tokens * 3) AS TEXT), E' characters, including white space. The PROMPT begins with "<PROMPT>" and ends with "</PROMPT>". \n- Use available CONTEXT to improve your response, and tell the user specifically which CONTEXT you used in plain language (do not use programming markup or tags). The context begins with "<CONTEXT>" and ends with "</CONTEXT>". \n- Strictly comply with all response restrictions. Response restrictions start with <RESPONSE_RESTRICTIONS> and end with </RESPONSE_RESTRICTIONS>. \n\n<PROMPT>\n ', prompt, E'\n</PROMPT>\n\n') INTO llm_prompt; END IF;
    
    -- Enforce response restrictions
    IF response_restrictions IS NOT null THEN SELECT CONCAT(llm_prompt, E'<RESPONSE_RESTRICTIONS>\n\n ', response_restrictions, E' \n\n</RESPONSE_RESTRICTIONS>\n\n') INTO llm_prompt; END IF;
    
    -- Open the context tag
    SELECT CONCAT(llm_prompt, E'<CONTEXT>\n\n') INTO llm_prompt;
    
    -- Add conversation history
    IF enable_history is true THEN
        -- Check if this is the first interaction from this user
        SELECT COUNT(*) FROM conversation_history WHERE user_id = uid INTO interaction_history_count;
        
        -- Add last interaction to prompt
        SELECT CONCAT(llm_prompt, E'<LATEST_INTERACTION>\n==========\n',
            CASE
                WHEN interaction_history_count = 0 THEN E' First interaction\n'
                ELSE (SELECT CONCAT(E'**TIME**\n', datetime, E'\n\n**USER**\n', user_prompt, E'\n\n**AI**\n', ai_response, E'\n') FROM conversation_history WHERE user_id = uid ORDER BY datetime DESC LIMIT 1)
            END,
            E'\n==========\n</LATEST_INTERACTION>\n\n') INTO llm_prompt;
        
        -- Add other relevant interaction history to prompt
        IF interaction_history_count > 1 THEN
            WITH ch AS (
                SELECT * FROM conversation_history
                WHERE user_id = uid
                AND id < (SELECT id FROM conversation_history WHERE user_id = uid ORDER BY datetime DESC LIMIT 1)
                ORDER BY user_prompt_embedding <=> google_ml.embedding('text-embedding-005', prompt)::vector
                LIMIT 3
            )
            SELECT CONCAT(llm_prompt, E'<OTHER_INTERACTION_HISTORY>\n==========\n', STRING_AGG(CONCAT(E'**TIME**\n', datetime, E'\n\n**USER**\n ', user_prompt, E'\n\n**AI**\n', ai_response), E'\n==========\n<\OTHER_INTERACTION_HISTORY>\n\n'))
            INTO llm_prompt FROM ch;
        END IF;
    END IF;
    
    -- Add additional_context and examples
    IF additional_context IS NOT null THEN SELECT CONCAT(llm_prompt, E'<ADDITIONAL_CONTEXT> Use the following CONTEXT to respond to the PROMPT, and tell me specifically which pieces of CONTEXT you used to improve your response:\n\n ', additional_context, E' </ADDITIONAL_CONTEXT>\n\n') INTO llm_prompt; END IF;
    IF examples IS NOT null THEN SELECT CONCAT(llm_prompt, E'<EXAMPLES> Use the following EXAMPLES to improve your OUTPUT.\n==========\n', examples, E' \n==========\n</EXAMPLES>\n\n') INTO llm_prompt; END IF;
    
    -- Add output instructions, format, and length constraints
    IF output_instructions IS NOT null THEN SELECT CONCAT(llm_prompt, E'<OUTPUT_INSTRUCTIONS> \nRe-write your OUTPUT using the following instructions:\n', output_instructions, E' \n</OUTPUT_INSTRUCTIONS>\n\n') INTO llm_prompt; END IF;
    IF output_format IS NOT null THEN SELECT CONCAT(llm_prompt, '<OUTPUT_FORMAT> Complete the TASK using the following OUTPUT FORMAT: ', output_format, E' </OUTPUT_FORMAT>\n\n') INTO llm_prompt; END IF;
    
    -- Do stock lookup if enabled
    IF enable_stock_lookup is true THEN
        SELECT CONCAT(E'List 3 words that best describe the type of investment this person is looking for based on their QUESTION, RISK_PROFILE, and BIO. \n\nQUESTION:\n', prompt, E'\n\nRISK_PROFILE: \n', risk_profile, E'\n\nBIO: \n', bio) INTO extractive_prompt FROM user_profiles WHERE id = uid;
        SELECT google_ml.predict_row(model, json_build_object(
		'contents', json_build_array(
			json_build_object(
				'role', 'user',
				'parts', json_build_array(
					json_build_object(
						'text', extractive_prompt
					)
				)
			)
		),
		'generationConfig', json_build_object(
			'temperature', temperature,
			'topP', top_p,
			'topK', top_k,
			'maxOutputTokens', max_output_tokens
		))) -> 'candidates' -> 0 -> 'content' -> 'parts' -> 0 ->> 'text' INTO extractive_response;
        
        WITH inv AS (
            SELECT ticker, analysis
            FROM investments
            WHERE rating = 'BUY'
            ORDER BY analysis_embedding <=> google_ml.embedding('text-embedding-005',extractive_response)::vector
            LIMIT 3
        )
        SELECT
            CONCAT(llm_prompt, E'<SUGGESTED_STOCKS> Recommend these specific stock tickers to me, and tell me why they are a good fit for me based on my BIO and personal details: ', STRING_AGG(ticker, ', '), E'\n\nTicker Details: ', STRING_AGG(CONCAT(E'\n========\n**STOCK TICKER**: ', ticker, E'\n\n', analysis), E'\n'), E'\n========\n</SUGGESTED_STOCKS>\n\n'),
            CONCAT('Tickers: ', STRING_AGG(ticker, ', '))
        FROM inv
        INTO llm_prompt, recommended_tickers;
    END IF;
    
    -- Close the context tag
    SELECT CONCAT(llm_prompt, E'</CONTEXT>\n\n') INTO llm_prompt;
    
    -- Send enriched prompt to LLM
    IF set_debug is false THEN
        SELECT google_ml.predict_row(model, json_build_object(
            'contents', json_build_array(
                json_build_object(
                    'role', 'user',
                    'parts', json_build_array(
                        json_build_object(
                            'text', llm_prompt
                        )
                    )
                )
            ),
            'generationConfig', json_build_object(
                'temperature', temperature,
                'topP', top_p,
                'topK', top_k,
                'maxOutputTokens', max_output_tokens
            ))) -> 'candidates' -> 0 -> 'content' -> 'parts' -> 0 ->> 'text' INTO llm_response;

    END IF;
    
    -- Record conversation history
    IF enable_history is true THEN
        INSERT INTO conversation_history (user_id, user_prompt, ai_response)
        VALUES (uid, prompt, llm_response);
    END IF;
    
    -- Add disclaimer
    IF disclaimer IS NOT null THEN SELECT CONCAT(llm_response, E'\n\n', disclaimer) INTO llm_response; END IF;
    
    -- Return the response
    RETURN QUERY SELECT llm_prompt, LENGTH(llm_prompt), llm_response, LENGTH(llm_response), extractive_prompt, extractive_response, recommended_tickers;
END;
$$;
