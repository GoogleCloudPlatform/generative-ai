"""This is a python utility file."""

POLICIES = [
    "Home Shield",
    "Bharat Griha Raksha Plus",
    "Micro Insurance - Home Insurance",
    "My Asset Home Insurance",
]

POLICY_SOURCES = [
    "gs://teamindrdhanush-agent-assist/Home_Insurance/policy-wording-home-shield.pdf",
    "gs://teamindrdhanush-agent-assist/Home_Insurance/bharat-griha-raksha-plus-pw.pdf",
    "gs://teamindrdhanush-agent-assist/Home_Insurance/micro-insurance---home-insurance.pdf",
    "gs://teamindrdhanush-agent-assist/Home_Insurance/ma-home-insurance-premium-pw.pdf",
]

SOURCE_TO_POLICY = {}

for i in range(len(POLICIES)):
    SOURCE_TO_POLICY[POLICY_SOURCES[i]] = POLICIES[i]
