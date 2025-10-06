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
CREATE OR REPLACE FUNCTION public.llm_local(
    set_debug boolean DEFAULT false,
    enable_history boolean DEFAULT false,
    uid integer DEFAULT 2147483647,
    model text DEFAULT 'llama2-70B'::text,
    user_role text DEFAULT 'I am a generic user'::text,
    llm_role text DEFAULT ' You are a helpful AI Assistant'::text,
    mission text DEFAULT null::text,
    additional_context text DEFAULT null::text,
    output_format text DEFAULT null::text,
    examples text DEFAULT null::text,
    prompt text DEFAULT 'Tell me I need to pass in a prompt parameter.'::text,
    output_instructions text DEFAULT null::text,
    response_restrictions text DEFAULT 'You have no response restrictions for this prompt.'::text,
    disclaimer text DEFAULT null::text,
    max_output_tokens integer DEFAULT 512,
    temperature numeric DEFAULT 0.0,
    top_p numeric DEFAULT 0.95,
    top_k numeric DEFAULT 40
)
RETURNS TABLE (
    llm_prompt text,
    llm_prompt_len integer,
    llm_response text,
    llm_response_len integer
)
LANGUAGE plpgsql
AS $function$
DECLARE
    llm_prompt TEXT := '';
    llm_prompt_len INT := null;
    llm_response TEXT := null;
    interaction_history_count INT := 0;
	request_id TEXT := gen_random_uuid()::text;
BEGIN
    SELECT CONCAT('Starting request id: ', request_id, E'\n\n') INTO llm_prompt;
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
    
    -- Close the context tag
    SELECT CONCAT(llm_prompt, E'</CONTEXT>\n\n') INTO llm_prompt;

	-- Define end of the request
	SELECT CONCAT(llm_prompt, 'Ending request id: ', request_id, E'\n\n') INTO llm_prompt;
    
    -- Send enriched prompt to LLM
	SELECT split_part(google_ml.predict_row(model, json_build_object(
		'prompt', llm_prompt,
		'max_tokens', max_output_tokens,
		'top_p', top_p,
		'temperature', temperature)
	) -> 'predictions' ->> 0, E'Output:', 2) INTO llm_response;

    -- Record conversation history
    IF enable_history is true THEN
        INSERT INTO conversation_history (user_id, user_prompt, ai_response)
        VALUES (uid, prompt, llm_response);
    END IF;
    
    -- Add disclaimer
    IF disclaimer IS NOT null THEN SELECT CONCAT(llm_response, E'\n\n', disclaimer) INTO llm_response; END IF;
    
    -- Return the response
    RETURN QUERY SELECT llm_prompt, LENGTH(llm_prompt), llm_response, LENGTH(llm_response);
END;
$function$
