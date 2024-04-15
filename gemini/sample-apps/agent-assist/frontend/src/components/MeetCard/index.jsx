import "./loader.css";

const MeetCard = ({ payload }) => {
  // payload is the event object from the Google Calendar API
  console.log("payload", payload);
  const event = payload;

  // startDate and endDate are Date objects representing the start and end times of the event
  const startDate = new Date(event.start.dateTime);
  const endDate = new Date(event.end.dateTime);

  // timeOptions is a configuration object for the toLocaleString() method, which formats the date and time
  const timeOptions = {
    hour: "numeric",
    minute: "numeric",
    hour12: true,
  };

  // formattedStartTime and formattedEndTime are strings representing the formatted start and end times of the event
  const formattedStartTime = startDate.toLocaleString("en-US", timeOptions);
  const formattedEndTime = endDate.toLocaleString("en-US", timeOptions);

  // formattedRange is a string representing the formatted range of the event, including the weekday, month, day, start time, and end time
  const formattedRange = `${startDate.toLocaleString("en-US", { weekday: "long", month: "long", day: "numeric" })} · ${formattedStartTime} – ${formattedEndTime}`;

  return (
    <div className="courses-container">
      <div className="course">
        <div className="course-preview">
          <h6>Google Meet</h6>
          <h2>Video Meeting</h2>
          <a href="#">
            <i className="fas fa-chevron-right"></i>
          </a>
        </div>
        <div className="course-info">
          <h6>{event.summary}</h6>
          <h6>{formattedRange}</h6>
          <h6>Time zone: {event.start.timeZone}</h6>
          <h6>Google Meet joining info</h6>
          <h6>
            Link:{" "}
            <a href="https://meet.google.com/bwc-hmfg-akh" target="_blank">
              https://meet.google.com/bwc-hmfg-akh
            </a>
          </h6>
          <h6>Or dial: ‪(IN) +91 22 7127 9696‬</h6>
        </div>
      </div>
    </div>
  );
};

export default MeetCard;
