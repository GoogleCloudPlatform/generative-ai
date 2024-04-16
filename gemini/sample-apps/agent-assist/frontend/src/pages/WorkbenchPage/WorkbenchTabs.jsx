import CustomerManagement from "./CustomerManagement";
import LeadsSales from "./LeadsSales";
import Marketing from "./Marketing";
import Performance from "./Performance";

const WorkbenchTabs = ({ value, startDate, endDate, period }) => {
  const formattedStartDate = startDate.format("YYYY-MM-DD");
  const formattedEndDate = endDate.format("YYYY-MM-DD");

  switch (value) {
    case 0:
      return (
        <Performance
          performanceStartDate={formattedStartDate}
          performanceEndDate={formattedEndDate}
          period={period}
        />
      );
    case 1:
      return (
        <LeadsSales
          leadsSalesStartDate={formattedStartDate}
          leadsSalesEndDate={formattedEndDate}
          period={period}
        />
      );
    case 2:
      return (
        <CustomerManagement
          customerManagementStartDate={formattedStartDate}
          customerManagementEndDate={formattedEndDate}
          period={period}
        />
      );
    case 3:
      return (
        <Marketing
          marketingStartDate={formattedStartDate}
          marketingEndDate={formattedEndDate}
          period={period}
        />
      );
    default:
      return null;
  }
};

export default WorkbenchTabs;
