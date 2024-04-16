import { Grid, Stack, Typography } from "@mui/material";
import Skeleton from "@mui/material/Skeleton";
import { Fragment, useState } from "react";
import axios from "../../apis/list_of_users";
import AppointmentList from "../../components/AppointmentList";
import EnhancedTable from "../../components/EnhancedTable";
import EnhancedTablePotential from "../../components/EnhancedTablePotential";
import KanbanBoard from "../../components/KanbanBoard";
import PopUpContacted from "../../components/PopUpContacted";
import PopUpKanban from "../../components/PopUpKanban";
import PopUpPotential from "../../components/PopUpPotential";
import useAxios from "../../hooks/useAxios";

const AgentAssist = () => {
  const [kanbanrow, setKanbanRow] = useState({});
  const [popUpRow, setPopUpRow] = useState({});
  const [openPopUp, setOpenPopUp] = useState(false);
  const [openPotPopUp, setOpenPotPopUp] = useState(false);
  const [openKanbanPopUp, setOpenKanbanPopUp] = useState(false);

  // Fetch Contacted Customers data using the useAxios hook
  const [contactedTableData, error, loading, setReload] = useAxios({
    axiosInstance: axios,
    method: "GET",
    url: "/contacted",
  });

  // Fetch Potential Customers data using the useAxios hook
  const [potentialTableData, error1, loading1, setReload1] = useAxios({
    axiosInstance: axios,
    method: "GET",
    url: "/potential",
  });

  // Fetch Appointment data using the useAxios hook
  const [appointmentData, error2, loading2, setReload2] = useAxios({
    axiosInstance: axios,
    method: "GET",
    url: "/get_calendar_events",
  });

  console.log("appointmentData", appointmentData);
  return (
    <>
      <Fragment>
        <Grid container columns={10} alignSelf="center">
          <Typography
            sx={{ flex: "1 1 100%" }}
            variant="h4"
            id="tableTitle"
            component="div"
            align="center"
            color="primary"
          >
            Agent-Assist
          </Typography>
          <br />
          <br />
          <br />
        </Grid>
        <Grid container spacing={3} alignItems="center" justifyContent="center">
          <Grid item sm={6}>
            {Object.keys(contactedTableData).length === 0 ? ( // Check if Contacted Customers data is empty
              <Skeleton variant="rectangular">
                <EnhancedTable
                  tableData={contactedTableData}
                  setPopUpRow={setPopUpRow}
                  setOpenPopUp={setOpenPopUp}
                />
              </Skeleton>
            ) : (
              <Fragment>
                <EnhancedTable
                  tableData={contactedTableData}
                  setPopUpRow={setPopUpRow}
                  setOpenPopUp={setOpenPopUp}
                  text="Contacted Customers"
                />
                <PopUpContacted
                  openPopUp={openPopUp}
                  setOpenPopUp={setOpenPopUp}
                  row={popUpRow}
                  isReviewer={true}
                />
              </Fragment>
            )}

            <Stack
              sx={{ pt: 4 }}
              direction="row"
              spacing={10}
              justifyContent="end"
            ></Stack>
          </Grid>
        </Grid>
        <Grid container spacing={3} alignItems="top" justifyContent="center">
          <Grid item sm={3}>
            {Object.keys(potentialTableData).length === 0 ? ( // Check if Potential Customers data is empty
              <Skeleton variant="rectangular">
                <EnhancedTablePotential
                  tableData={potentialTableData}
                  setPopUpRow={setPopUpRow}
                  setOpenPopUp={setOpenPotPopUp}
                />
              </Skeleton>
            ) : (
              <Fragment>
                <EnhancedTablePotential
                  tableData={potentialTableData}
                  setPopUpRow={setPopUpRow}
                  setOpenPopUp={setOpenPotPopUp}
                  text="Potential Customers"
                />
                <PopUpPotential
                  openPopUp={openPotPopUp}
                  setOpenPopUp={setOpenPotPopUp}
                  row={popUpRow}
                  isReviewer={true}
                />
              </Fragment>
            )}

            <Stack
              sx={{ pt: 4 }}
              direction="row"
              spacing={10}
              justifyContent="end"
            ></Stack>
          </Grid>
          <Grid item sm={3}>
            <AppointmentList payload={appointmentData} />
          </Grid>
        </Grid>
        <Grid container spacing={3} alignItems="center" justifyContent="center">
          <Grid item sm={8}>
            <Fragment>
              <KanbanBoard
                setOpenPopUp={setOpenKanbanPopUp}
                setKanbanRow={setKanbanRow}
              />
              <PopUpKanban
                openPopUp={openKanbanPopUp}
                setOpenPopUp={setOpenKanbanPopUp}
                row={kanbanrow}
              />
            </Fragment>
          </Grid>
        </Grid>
      </Fragment>
    </>
  );
};

export default AgentAssist;
