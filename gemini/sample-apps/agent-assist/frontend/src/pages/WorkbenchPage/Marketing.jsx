import { Grid } from "@mui/material";
import axios from "axios";
import { useEffect, useState } from "react";
import MarketingChart from "../../components/Chart/MarketingChart";
import DisplayCard from "../../components/DisplayCard";
const BACKENDURL = process.env.REACT_APP_API_URL;

const Marketing = (props) => {
  const { marketingStartDate, marketingEndDate, period } = props;
  const [marketingAndOutreachData, setMarketingAndOutreachData] = useState({});
  function fetchData() {
    axios
      .get(
        `${BACKENDURL}/workbench/marketingandoutreach?startDate=${marketingStartDate}&endDate=${marketingEndDate}`,
      )
      .then((res) => {
        setMarketingAndOutreachData(res.data);
      })
      .catch((err) => {
        console.log(err);
      });
  }

  // Use useEffect to fetch data when startDate or endDate changes
  useEffect(() => {
    fetchData();
  }, [marketingStartDate, marketingEndDate]);

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
              metric="Website Traffic"
              value={marketingAndOutreachData.websiteTraffic}
              period={period}
              animation={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Emails Sent"
              value={marketingAndOutreachData.emailsent}
              period={period}
              animation={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Emails Open Rate"
              value={marketingAndOutreachData.openrate}
              period={period}
              animation={true}
              percent={true}
              decimal={true}
            />
          </Grid>

          <Grid item xs={4}>
            <DisplayCard
              metric="Social Media Likes"
              value={marketingAndOutreachData.likes}
              period={period}
              animation={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Social Media Comments"
              value={marketingAndOutreachData.comments}
              period={period}
              animation={true}
            />
          </Grid>
          <Grid item xs={4}>
            <DisplayCard
              metric="Social Media Shares"
              value={marketingAndOutreachData.shares}
              period={period}
              animation={true}
            />
          </Grid>

          <Grid item xs={12}>
            <MarketingChart
              data={marketingAndOutreachData.chartData}
              period={period}
            />
          </Grid>
        </Grid>
      </div>
    </>
  );
};

export default Marketing;
