import axios from "axios";
const BACKENDURL = process.env.REACT_APP_API_URL;
const BASE_URL = BACKENDURL + "/users";

export default axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-type": "text/markdown",
    Accept: "text/markdown",
  },
});
