import { IconButton } from "@material-ui/core";
import AppBar from "@material-ui/core/AppBar";
import Grid from "@material-ui/core/Grid";
import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import {
  ThemeProvider,
  createTheme,
  makeStyles,
} from "@material-ui/core/styles";
import InfoIcon from "@mui/icons-material/Info";
import axios from "axios";
import React, { useEffect, useState } from "react";
import { DragDropContext, Draggable, Droppable } from "react-beautiful-dnd";

// Initial data for the Kanban board
const initialData = {
  columns: {
    "initial-contact": {
      id: "initial-contact",
      title: "Initial Contact",
      userIds: [],
    },
    "needs-analysis": {
      id: "needs-analysis",
      title: "Needs Analysis",
      userIds: [],
    },
    "proposal-sent": {
      id: "proposal-sent",
      title: "Proposal Sent",
      userIds: [],
    },
    followup: {
      id: "followup",
      title: "Follow-up",
      userIds: [],
    },
    closed: {
      id: "closed",
      title: "Closed",
      userIds: [],
    },
  },
  users: {},
};

// Create a custom theme for the Kanban board
const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
    },
  },
});

// Create styles for the Kanban board
const useStyles = makeStyles((theme) => ({
  root: {
    flexGrow: 1,
    padding: theme.spacing(2),
  },
  appBar: {
    backgroundColor: theme.palette.primary.main,
  },
  column: {
    padding: theme.spacing(2),
    minHeight: "200px",
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
  },
}));

// Main KanbanBoard component
const KanbanBoard = ({ setOpenPopUp, setKanbanRow }) => {
  const classes = useStyles();
  const [data, setData] = useState(initialData);
  const BACKENDURL = process.env.REACT_APP_API_URL;

  // Fetch data from the backend on component mount
  useEffect(() => {
    axios
      .get(`${BACKENDURL}/agent-assist/kanban`)
      .then((respone) => {
        var newData = initialData;
        console.log("hello", respone.data.data);
        newData.columns["initial-contact"].userIds =
          respone.data["initial-contact"];
        newData.columns["needs-analysis"].userIds =
          respone.data["needs-analysis"];
        newData.columns["proposal-sent"].userIds =
          respone.data["proposal-sent"];
        newData.columns["followup"].userIds = respone.data["followup"];
        newData.columns["closed"].userIds = respone.data["closed"];
        newData.users = respone.data["users"];
        setData(newData);
        console.log("data", newData);
      })
      .catch((err) => {
        console.log(err);
      });
    const newData =
      JSON.parse(localStorage.getItem("kanbanData")) || initialData;
    setData(newData);
  }, []);

  // Handle click on a user card
  const handleClick = (userId) => {
    setOpenPopUp(true);
    setKanbanRow(data.users[userId]);
  };

  // Handle drag and drop of user cards
  const onDragEnd = (result) => {
    const { destination, source, draggableId } = result;

    // If the destination is undefined, return
    if (!destination) return;

    // If the destination and source are the same, return
    if (
      destination.droppableId === source.droppableId &&
      destination.index === source.index
    ) {
      return;
    }

    // Get the start and finish columns
    const start = data.columns[source.droppableId];
    const finish = data.columns[destination.droppableId];

    // If the start and finish columns are the same, update the userIds array
    if (start === finish) {
      const newUserIds = Array.from(start.userIds);
      newUserIds.splice(source.index, 1);
      newUserIds.splice(destination.index, 0, draggableId);

      const newColumn = {
        ...start,
        userIds: newUserIds,
      };

      const newData = {
        ...data,
        columns: {
          ...data.columns,
          [newColumn.id]: newColumn,
        },
      };
      setData(newData);
    } else {
      // If the start and finish columns are different, update the userIds arrays of both columns
      const startUserIds = Array.from(start.userIds);
      startUserIds.splice(source.index, 1);
      const newStart = {
        ...start,
        userIds: startUserIds,
      };

      const finishUserIds = Array.from(finish.userIds);
      finishUserIds.splice(destination.index, 0, draggableId);
      const newFinish = {
        ...finish,
        userIds: finishUserIds,
      };

      const newData = {
        ...data,
        columns: {
          ...data.columns,
          [newStart.id]: newStart,
          [newFinish.id]: newFinish,
        },
      };
      // Send a POST request to the backend to update the database
      axios.post(`${BACKENDURL}/agent-assist/kanban/update`, {
        fromCol: source.droppableId,
        toCol: destination.droppableId,
        id: draggableId,
      });
      setData(newData);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <AppBar position="static" className={classes.appBar}></AppBar>
      <div className={classes.root}>
        <DragDropContext onDragEnd={onDragEnd}>
          <Grid container spacing={2}>
            {Object.values(data.columns).map((column) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={column.id}>
                <Paper
                  className={classes.column}
                  style={{ backgroundColor: "#1976D2" }}
                >
                  <Typography variant="h6">{column.title}</Typography>
                  <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        style={{
                          backgroundColor: snapshot.draggingFromThisWith
                            ? "#1976D2"
                            : snapshot.isDraggingOver
                              ? "#4E9CEA"
                              : "#1976D2",
                          border: "2px",
                          overflowY: "overlay",
                          maxHeight: "250px",
                          minHeight: "250px",
                        }}
                        {...provided.droppableProps}
                      >
                        {column.userIds.map((userId, index) => (
                          <Draggable
                            key={userId}
                            draggableId={userId}
                            index={index}
                          >
                            {(provided) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                              >
                                <Paper
                                  elevation={10}
                                  style={{ padding: 10, marginBottom: 10 }}
                                >
                                  {data.users[userId].Name}
                                  <IconButton
                                    variant="contained"
                                    onClick={() => handleClick(userId)}
                                    size="small"
                                    style={{ float: "right" }}
                                  >
                                    <InfoIcon fontSize="small" />
                                  </IconButton>
                                </Paper>
                              </div>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </Paper>
              </Grid>
            ))}
          </Grid>
        </DragDropContext>
      </div>
    </ThemeProvider>
  );
};

export default KanbanBoard;
