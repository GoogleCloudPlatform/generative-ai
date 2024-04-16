import axios from "axios";
const BACKENDURL = process.env.REACT_APP_API_URL;

const axios_workbench = axios.create({
  baseURL: BACKENDURL,
  headers: {
    "Content-type": "application/json",
    Accept: "application/json",
    withCredentials: true,
  },
});

export default axios_workbench;
