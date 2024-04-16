import { Grid } from "@mui/material";
import axios from "axios";
import { useEffect, useState } from "react";
import CustomerManagementChart from "../../components/Chart/CustomerChart";
import DisplayCard from "../../components/DisplayCard";

// CustomerManagement component displays customer management metrics and a chart
const CustomerManagement = (props) => {
  const { customerManagementStartDate, customerManagementEndDate, period } = props;
  const BACKENDURL = process.env.REACT_APP_API_URL;
  const [customerManagementData, setCustomerManagementData] = useState({});
  function fetchData() {
    axios
      .get(
        `${BACKENDURL}/workbench/customermanagement?startDate=${customerManagementStartDate}&endDate=${customerManagementEndDate}`,
      )
      .then((res) => {
        setCustomerManagementData(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }
  // useEffect to fetch data when startDate or endDate changes
  useEffect(() => {
    fetchData();
  }, [customerManagementStartDate, customerManagementEndDate]);

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
              metric="Active Customers"
              value={customerManagementData.totalActiveCustomers}
              period={period}
              animation={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Avg Satisfaction Score"
              value={customerManagementData.averageSatisfactionScore}
              period={period}
              animation={true}
              decimal={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Lapsed Customers"
              value={customerManagementData.totalLapsedCustomers}
              period={period}
              animation={true}
            />
          </Grid>

          <Grid item xs={12}>
            <CustomerManagementChart
              data={customerManagementData.chartData}
              period={period}
            />
          </Grid>
          <Grid item xs={12}>
            <DisplayCard
              metric="Top Reasons for Lapse"
              value="Change of residence, Price concerns"
              period={period}
            />
          </Grid>
        </Grid>
      </div>
    </>
  );
};

export default CustomerManagement;
