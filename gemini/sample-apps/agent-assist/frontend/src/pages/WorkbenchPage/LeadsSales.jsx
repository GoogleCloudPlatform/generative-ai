import { Grid } from "@mui/material";
import axios from "axios";
import { useEffect, useState } from "react";
import LeadsChart from "../../components/Chart/LeadsChart";
import DisplayCard from "../../components/DisplayCard";

const LeadsSales = (props) => {
  const { leadsSalesStartDate, leadsSalesEndDate, period } = props;
  const BACKENDURL = process.env.REACT_APP_API_URL;
  const [leadsAndSalesData, setLeadsAndSalesData] = useState({});
  function fetchData() {
    axios
      .get(
        `${BACKENDURL}/workbench/leadsandsales?startDate=${leadsSalesStartDate}&endDate=${leadsSalesEndDate}`,
      )
      .then((res) => {
        setLeadsAndSalesData(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }

  // Use useEffect to fetch data when startDate or endDate changes
  useEffect(() => {
    fetchData();
  }, [leadsSalesStartDate, leadsSalesEndDate]);

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
        <Grid container spacing={2} justifyContent={"center"}>
          <Grid item xs={4}>
            <DisplayCard
              metric="Leads Generated" // Display card for leads generated
              value={leadsAndSalesData.leadsGenerated} // Set the value from the state
              period={period} // Set the period from props
              animation={true} // Enable animation
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Lead Conversion Rate" // Display card for lead conversion rate
              value={leadsAndSalesData.conversionRate} // Set the value from the state
              period={period} // Set the period from props
              animation={true} // Enable animation
              percent={true} // Display as a percentage
              decimal={true} // Display with decimal places
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Sales Pipeline Value" // Display card for sales pipeline value
              value={leadsAndSalesData.revenueGenerated} // Set the value from the state
              period={period} // Set the period from props
            />
          </Grid>
          <Grid item xs={12}>
            <LeadsChart data={leadsAndSalesData.platformData} />{" "}
            {/* Display the leads chart */}
          </Grid>
          <Grid item xs={8}>
            <DisplayCard
              metric="Top Performing Policy" // Display card for top performing policy
              value={leadsAndSalesData.topPerformingPolicy} // Set the value from the state
              period={period} // Set the period from props
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Top Performing Platform" // Display card for top performing platform
              value={leadsAndSalesData.topPerformingPlatform} // Set the value from the state
              period={period} // Set the period from props
            />
          </Grid>
        </Grid>
      </div>
    </>
  );
};

export default LeadsSales;
