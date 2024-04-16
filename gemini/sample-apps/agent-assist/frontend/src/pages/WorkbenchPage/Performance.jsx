import { Grid } from "@mui/material";
import axios from "axios";
import { useEffect, useState } from "react";
import PerformanceChart from "../../components/Chart/PerformanceChart";
import DisplayCard from "../../components/DisplayCard";

// Performance component displays performance metrics and a chart
const Performance = (props) => {
  const { performanceStartDate, performanceEndDate, period } = props;
  const [performanceData, setPerformanceData] = useState({});

  // API endpoint URL
  const BACKENDURL = process.env.REACT_APP_API_URL;

  // Function to fetch performance data from the backend
  function fetchData() {
    axios
      .get(
        `${BACKENDURL}/workbench/performance?startDate=${performanceStartDate}&endDate=${performanceEndDate}`
      )
      .then((res) => {
        setPerformanceData(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }

  // Fetch data when startDate or endDate changes
  useEffect(() => {
    fetchData();
  }, [performanceStartDate, performanceEndDate]);

  return (
    <>
      <div
        style={{
          marginTop: "20px",
          width: "70%",
          alignItems: "center",
          marginLeft: "15%",
        }}
      >
        <Grid container spacing={5} justifyContent={"center"}>
          <Grid item xs={4}>
            <DisplayCard
              metric="Policies Sold"
              value={performanceData.numberOfPoliciesSold}
              period={period}
              animation={true} // Enable animation for this card
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Revenue Generated"
              value={performanceData.revenueGenerated}
              period={period}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Renewal Rate"
              value={performanceData.renewalRate}
              period={period}
              animation={true} // Enable animation for this card
              percent={true} // Display value as a percentage
              decimal={true} // Display value with one decimal place
            />
          </Grid>
          <Grid item xs={12}>
            <PerformanceChart data={performanceData.monthData} />
          </Grid>
        </Grid>
      </div>
    </>
  );
};

export default Performance;
