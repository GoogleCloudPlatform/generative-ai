import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import NativeSelect from "@mui/material/NativeSelect";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import dayjs from "dayjs";
import * as React from "react";
import WorkbenchTabs from "./WorkbenchTabs";

export default function WorkBenchPage() {
  // State for the current tab
  const [value, setValue] = React.useState(0);
  // State for the end date
  const [endDate, setEndDate] = React.useState(dayjs("2023-12-31"));
  // State for the start date
  const [startDate, setStartDate] = React.useState(
    endDate.subtract(12, "month")
  );
  // Calculate the period based on the start and end dates
  let period = "";
  const dayDiff = endDate.diff(startDate, "day") % 365;
  const monthDiff = endDate.diff(startDate, "month") % 12;
  const yearDiff = endDate.diff(startDate, "year");
  if (yearDiff > 0) {
    period = `${yearDiff} ${yearDiff > 1 ? " years " : " year "}`;
  }
  if (monthDiff > 0) {
    period += `${monthDiff} ${monthDiff > 1 ? " months " : " month "}`;
  } else if (dayDiff > 0) {
    period += `${dayDiff} ${dayDiff > 1 ? " days " : " day "}`;
  }
  period = period.trim();
  // Handle the change of the tab
  const handleChange = (event, number) => {
    setValue(number);
  };
  // Handle the change of the time period
  const handleChangeTimePeriod = (event) => {
    setStartDate(endDate.subtract(event.target.value, "month"));
  };

  return (
    <>
      <Box sx={{ width: "100%", bgcolor: "primary" }}>
        <Tabs value={value} onChange={handleChange} centered>
          <Tab label="Performance" />
          <Tab label="Leads and Sales" />
          <Tab label="Customer Management" />
          <Tab label="Marketing and Outreach" />
        </Tabs>
        <Box sx={{ display: "flex", justifyContent: "center", marginTop: 2 }}>
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DatePicker
              sx={{ marginRight: 2, borderColor: "primary" }}
              label="Start Date"
              value={startDate}
              onChange={setStartDate}
              maxDate={endDate.subtract(1, "day")}
            />
            <DatePicker
              label="End Date"
              value={endDate}
              minDate={startDate.add(1, "day")}
              onChange={setEndDate}
              maxDate={dayjs()}
            />
          </LocalizationProvider>
          <Box sx={{ minWidth: 120, paddingLeft: 2 }}>
            <FormControl fullWidth>
              <InputLabel variant="standard" htmlFor="uncontrolled-native">
                Time period
              </InputLabel>
              <NativeSelect defaultValue={12} onChange={handleChangeTimePeriod}>
                <option value={1}>1 Month</option>
                <option value={3}>3 Months</option>
                <option value={6}>6 Months</option>
                <option value={12}>1 Year</option>
                <option value={24}>2 Years</option>
                <option value={60}>5 Years</option>
              </NativeSelect>
            </FormControl>
          </Box>
        </Box>
      </Box>
      <WorkbenchTabs
        value={value}
        startDate={startDate}
        endDate={endDate}
        period={period}
      />
    </>
  );
}
