def get_extract_entities_prompt() -> str:
    """Definition of prompt to extract data from a W-2 Tax Form"""
    return """
    Task: Extract W-2 Tax Form Information

    Objective:
    Accurately identify and extract the following fields from the provided document, which is expected to be a W-2 tax form or a representation thereof:

    * Employee's Social Security Number
    * Employer Identification Number (EIN)
    * Employee's Name
    * Employer's Name
    * Employer's Address
    * Control Number (if present)
    * Wages, Tips, and Other Compensation (Box 1)
    * Federal Income Tax Withheld (Box 2)
    * Social Security Wages (Box 3)
    * Social Security Tax Withheld (Box 4)
    * Medicare Wages and Tips (Box 5)
    * Medicare Tax Withheld (Box 6)
    * Social Security Tips (Box 7)
    * Allocated Tips (Box 8)
    * Dependent Care Benefits (Box 10)
    * Nonqualified Plan Contributions (Box 11)
    * State and Local Information (Boxes 15-20):
        * State
        * Employer's State ID Number
        * State Wages, Tips, Etc.
        * State Income Tax Withheld
        * Local Wages, Tips, Etc.
        * Local Income Tax Withheld
        * Locality Name

    Guidelines:

    * Prioritize accuracy. If a field cannot be confidently extracted, indicate it as "Not Found" or a similar placeholder.
    * Handle variations in document formatting and layout.
    * If the document contains multiple W-2 forms, extract information for each one separately.
    * Format the extracted data in a structured manner, such as a JSON object or a table, for easy further processing.

    Example Output (JSON):

    ```
    {
        "Employee's Social Security Number": "***-**-****",
        "Employer Identification Number (EIN)": "**-*******",
        "Employee's Name": "John Doe",
        "Employer's Name": "Acme Corporation",
        "Employer's Address": "123 Main Street, Town, USA",
        "Control Number": "12345",
        "Wages, Tips, and Other Compensation (Box 1)": "50000.00",
        "Federal Income Tax Withheld (Box 2)": "5000.00",
        "Social Security Wages (Box 3)": "45000.00",
        "Social Security Tax Withheld (Box 4)": "2800.00",
        "Medicare Wages and Tips (Box 5)": "50000.00",
        "Medicare Tax Withheld (Box 6)": "725.00",
        "Social Security Tips (Box 7)": "0.00",
        "Allocated Tips (Box 8)": "0.00",
        "Dependent Care Benefits (Box 10)": "0.00",
        "Nonqualified Plan Contributions (Box 11)": "0.00",
        "State": "CA",
        "Employer's State ID Number": "123456789",
        "State Wages, Tips, Etc.": "50000.00",
        "State Income Tax Withheld": "2000.00",
        "Local Wages, Tips, Etc.": "0.00",
        "Local Income Tax Withheld": "0.00",
        "Locality Name":""
    }
    """


def get_compare_entities_prompt() -> str:
    """Definition of prompt to compare output from DocumentAI and Gemini"""
    return """
    **Analyze and compare the following two outputs, one from DocumentAI and the other from Gemini. Identify and list the following:**

    * **Similarities:** Entities or data points that are present and have the same values in both outputs.
    * **Differences:**
        * Entities present in one output but missing in the other.
        * Entities present in both but with differing values.

    **DocumentAI output:**
    ```{docai_output}```

    **Gemini output:**
    ```{gemini_output}```

    """
