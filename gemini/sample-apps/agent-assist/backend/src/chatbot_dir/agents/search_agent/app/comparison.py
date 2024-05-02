"""This is a python utility file."""

# pylint: disable=E0401

PROMPT_FOR_COMPARISON = """
You are a  home insurance domain expert who has a lot of knowledge about home insurance policies.
Your task is to thoroughly evaluate and compare various medical policies or recommend the most suitable policy from a given set.
To accomplish this, delve into the specifics of each policy's coverage.
Think step by step before answering.
Analyze and compare the provisions offered for specific conditions mentioned in the query,
considering the scope and depth of coverage for each policy.

Additionally, if possible, scrutinize the inclusions relevant to different age brackets,
ensuring a clear understanding of the coverage provided for various age groups.

Avoid any conjecture or assumptions while evaluating these policies.
Rely solely on the explicit information provided within each policy document.
Your aim is to provide a detailed and factual comparison or recommendation based solely on the information available within the policies.
This rigorous approach ensures an objective and accurate assessment, helping users make informed decisions regarding their home insurance choices.

---------------------------------------

INPUT: {}
OUTPUT: {}

---------------------------------------

INPUT: {}
OUTPUT: {}

---------------------------------------

INPUT: {}
OUTPUT: {}

---------------------------------------

INPUT: {query}
OUTPUT: """


def comparison(tb, query):
    """Function for policy comparison."""
    first_input = """
    Policy 1: MediCarePro Health Insurance
    Partial coverage for cataract surgery, including intraocular lens implants.
    --------------------------
    Policy 2: HealthSure Plus Insurance
    Full coverage for cataract surgery, including premium intraocular lens options.
    --------------------------
    Policy 3: VitalHealth Insurance
    Limited coverage for cataract surgery, covering only basic surgical procedures.
    --------------------------
    """

    first_output = """
    POLICY:  HealthSure Plus Insurance

    REASON: Upon evaluating the cataract coverage provided by these policies, HealthSure Plus Insurance emerges as the most comprehensive choice. It offers extensive coverage, including full support for cataract surgeries with premium intraocular lens options. This comprehensive coverage ensures a higher level of care and financial assistance for cataract treatments compared to the other policies assessed.

    On the other hand, while MediCarePro Health Insurance provides partial coverage for cataract surgeries with lens implants, it falls short of the comprehensive coverage offered by HealthSure Plus Insurance.

    VitalHealth Insurance, with its limited coverage for basic cataract procedures, provides minimal support for individuals seeking extensive coverage and advanced treatment options for cataract surgeries.

    Therefore, based solely on the explicit information available within the policies regarding cataract treatment, HealthSure Plus Insurance stands out as the recommended choice for comprehensive cataract coverage, ensuring optimal care and financial support for individuals requiring cataract surgeries.
    """

    second_input = """
    Policy 1: WellnessGuard Insurance
    Routine Health Checkup Coverage: WellnessGuard Insurance facilitates an inclusive regimen for routine health assessments, encompassing a diverse array of diagnostic evaluations and screenings to monitor health indicators proactively.
    --------------------------
    Policy 2: CareWell Assurance
    Routine Health Checkup Coverage: CareWell Assurance undertakes a meticulous approach to regular health evaluations. It integrates a spectrum of specialized medical tests and screenings aimed at vigilantly monitoring health status and identifying potential concerns in their nascent stages.
    --------------------------
    Policy 3: HealthyLife Plan
    Routine Health Checkup Coverage: HealthyLife Plan emphasizes a comprehensive strategy for routine health surveillance. It incorporates a range of diagnostic examinations and screenings designed to provide a thorough health assessment and early detection of potential health issues.
    --------------------------
    """

    second_output = """
    POLICY: WellnessGuard Insurance, CareWell Assurance, HealthyLife Plan

    REASON: Each policy—WellnessGuard Insurance, CareWell Assurance, and HealthyLife Plan—adopts a medical-oriented approach to routine health check-ups. They include a variety of diagnostic evaluations and screenings intended to vigilantly monitor health indicators and detect potential health issues at an early stage.

    Therefore, based on the explicit information within each policy regarding routine health checkup coverage, WellnessGuard Insurance, CareWell Assurance, and HealthyLife Plan equally emphasize comprehensive health monitoring, aiming to provide a thorough evaluation of health status and an early identification of potential health concerns.
    """

    third_input = """
    Policy 1: MediCareRx Plan
    Prescription Medication Coverage: MediCareRx Plan includes a wide range of prescription drugs, ensuring access to various medications for different health conditions.
    --------------------------
    Policy 2: PharmaGuard Plus
    Prescription Medication Coverage: PharmaGuard Plus offers an extensive formulary, providing access to diverse prescription medications for various health needs, similar to MediCareRx Plan.
    --------------------------
    Policy 3: HealthMinder Assurance
    Prescription Medication Coverage: HealthMinder Assurance supports access to necessary prescription medications for enrolled individuals.
    --------------------------
    """

    third_output = """
    POLICY: MediCareRx Plan, PharmaGuard Plus

    REASON: Both MediCareRx Plan and PharmaGuard Plus seem to offer similar prescription medication coverage. They highlight access to a broad array of prescription drugs, showcasing a diverse formulary without explicitly mentioning specific limitations or inclusions.

    Policy 3, HealthMinder Assurance, indicates providing access to necessary prescription medications, but the extent or diversity of medications isn’t explicitly detailed compared to the apparent formularies of the other two policies.

    Therefore, based on the explicit information available within each policy regarding prescription medication coverage, MediCareRx Plan and PharmaGuard Plus appear equally beneficial, showcasing a comprehensive formulary of prescription drugs for enrolled individuals.
    """

    fourth_input = """
    Policy: CareHaven Assurance
    Home Assistance Services Coverage: CareHaven Assurance offers a wide range of home assistance services, including skilled nursing care, physical therapy, and specialized medical equipment provisions for comprehensive in-home care.
    --------------------------
    Policy: ComfortCare Plan
    Home Assistance Services Coverage: ComfortCare Plan provides home assistance services, encompassing skilled nursing care and physical therapy similar to CareHaven Assurance.
    --------------------------
    """

    fourth_output = """
    POLICY: CareHaven Assurance

    REASON: Both CareHaven Assurance and ComfortCare Plan cover home assistance services, including skilled nursing care and physical therapy. However, CareHaven Assurance stands out by offering a more comprehensive range of home assistance services with the inclusion of specialized medical equipment provisions, ensuring a broader scope of in-home care compared to ComfortCare Plan, which provides similar services but lacks details on additional provisions like specialized medical equipment.

    Therefore, based on the explicit information available within each policy regarding home assistance services coverage, CareHaven Assurance logically appears to offer a more comprehensive range of in-home care services compared to ComfortCare Plan.
    """

    prompt = PROMPT_FOR_COMPARISON.format(
        first_input,
        first_output,
        second_input,
        second_output,
        third_input,
        third_output,
        fourth_input,
        fourth_output,
        query=query,
    )
    response = tb.generate_response(prompt)
    return response
