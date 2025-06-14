import React, { useState } from "react";
import { useRouter } from "next/router";
import Button from "../ui/Button";
import Input from "../ui/Input";
import Card from "../ui/Card";
import { startAnalysis } from "../../services/api";

export default function AnalysisForm() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    company_name: "",
    industry_name: "",
    num_use_cases: 5,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === "num_use_cases" ? parseInt(value, 10) : value,
    }));
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.company_name && !formData.industry_name) {
      newErrors.company_name =
        "Either company name or industry name is required";
      newErrors.industry_name =
        "Either company name or industry name is required";
    }

    if (
      formData.num_use_cases &&
      (formData.num_use_cases < 1 || formData.num_use_cases > 10)
    ) {
      newErrors.num_use_cases = "Number of use cases must be between 1 and 10";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setIsLoading(true);

    try {
      const request = {
        ...formData,
        // Clean empty strings
        company_name: formData.company_name || undefined,
        industry_name: formData.industry_name || undefined,
      };

      const response = await startAnalysis(request);
      router.push(`/results/${response.request_id}`);
    } catch (error) {
      console.error("Error starting analysis:", error);
      // Show error message
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card title="Generate AI Use Cases">
      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          id="company_name"
          name="company_name"
          label="Company Name"
          placeholder="e.g., ABC Steel"
          value={formData.company_name}
          onChange={handleChange}
          error={errors.company_name}
        />

        <Input
          id="industry_name"
          name="industry_name"
          label="Industry Name"
          placeholder="e.g., Manufacturing"
          value={formData.industry_name}
          onChange={handleChange}
          error={errors.industry_name}
        />

        <Input
          id="num_use_cases"
          name="num_use_cases"
          type="number"
          label="Number of Use Cases"
          min={1}
          max={10}
          value={formData.num_use_cases}
          onChange={handleChange}
          error={errors.num_use_cases}
        />

        <div className="flex justify-end">
          <Button type="submit" isLoading={isLoading}>
            Generate Use Cases
          </Button>
        </div>
      </form>
    </Card>
  );
}
