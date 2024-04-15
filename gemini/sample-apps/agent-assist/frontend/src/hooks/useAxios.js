import { useEffect, useState } from "react";

const useAxios = (configObj) => {
  // Destructure the config object to get the necessary properties
  const { axiosInstance, method, url, data, requestConfig = {} } = configObj;

  // Initialize the state variables
  const [response, setResponse] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  // Use the useEffect hook to make the API call
  useEffect(() => {
    // Create an AbortController to cancel the request if the component unmounts
    const controller = new AbortController();

    // Define the async function to fetch the data
    const fetchData = async () => {
      try {
        // Make the API call using the axios instance and the specified method, URL, and data
        const res = await axiosInstance[method.toLowerCase()](url, {
          ...requestConfig,
          signal: controller.signal,
          data: data,
        });
        // Log the response for debugging purposes
        console.log(res);
        // Update the response state with the data from the API call
        setResponse(res.data);
      } catch (err) {
        // If there is an error, update the error state with the error message
        setError(err.message);
      } finally {
        // Finally, set the loading state to false to indicate that the request is complete
        setLoading(false);
      }
    };

    // Call the fetchData function
    fetchData();

    // Return a cleanup function to cancel the request if the component unmounts
    return () => controller.abort();
  }, [reload]);

  // Return the response, error, loading, and setReload state variables
  return [response, error, loading, setReload];
};

export default useAxios;
