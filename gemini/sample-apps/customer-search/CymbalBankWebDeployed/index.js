const express = require("express");
const { readFileSync } = require("fs");
const handlebars = require("handlebars");
const fs = require("fs");
const path = require("path");
const dotenv = require("dotenv");
dotenv.config();
console.log(process.env.DF_AGENT_ID);
const app = express();

app.use(express.json());

app.use("/assets", express.static("assets"));
app.use("/public", express.static("public"));
app.use("/scripts", express.static("scripts"));
app.use("/style", express.static("style"));

const data = {
  service: process.env.k_service || "???",
  revision: process.env.k_revision || "???",
  df_agent_id: process.env.df_agent_id,
  project_id: process.env.project_id,
  credit_card_imagen_url: process.env.credit_card_imagen_url,
  rag_qa_chain_url_translate: process.env.rag_qa_chain_url_translate,
  user_login_url: process.env.user_login_url,
  apiKey: process.env.api_key,
  authDomain: process.env.auth_domain,
  projectId: process.env.project_id,
  storageBucket: process.env.storage_bucket,
  messagingSenderId: process.env.messaging_sender_id,
  appId: process.env.app_id,
  measurementId: process.env.measurement_id,
};

let template;
let template_search;
let template_saving;
let template_credit_card;
let template_custom_credit_card;
let template_neft;
let template_upi;
let template_imps;
let template_debit_card;
let template_recharge;
let template_electricity;
let template_insurance_premium;
let template_mutual_funds;
let template_ipo;
let template_stocks;
let template_current;
let template_salary;
let template_fixed_deposit;
let template_recurring_deposit;
let template_loans;
let template_saving_terms;
let template_calculator;
let template_credit_tc;
let template_loan_tc;
let template_loan_agreement;

function handleError(e) {
  console.error(e);
  res.status(500).send("Internal Server Error");
}

app.get("/", async (req, res) => {
  if (!template) {
    try {
      template = handlebars.compile(
        readFileSync("public/index.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/search", async (req, res) => {
  if (!template_search) {
    try {
      template_search = handlebars.compile(
        readFileSync("public/search.html.hbs", "utf8"),
      );
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  }
  try {
    const output = template_search(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/saving", async (req, res) => {
  if (!template_saving) {
    try {
      template_saving = handlebars.compile(
        readFileSync("public/saving.html.hbs", "utf8"),
      );
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  }
  try {
    const output = template_saving(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/credit_card", async (req, res) => {
  if (!template_credit_card) {
    try {
      template_credit_card = handlebars.compile(
        readFileSync("public/credit_card.html.hbs", "utf8"),
      );
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  }
  try {
    const output = template_credit_card(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/custom_credit_card", async (req, res) => {
  if (!template_custom_credit_card) {
    try {
      template_custom_credit_card = handlebars.compile(
        readFileSync("public/custom_credit_card.html.hbs", "utf8"),
      );
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  }
  try {
    const output = template_custom_credit_card(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/neft", async (req, res) => {
  if (!template_neft) {
    try {
      template_neft = handlebars.compile(
        readFileSync("public/neft.html.hbs", "utf8"),
      );
    } catch (e) {
      console.error(e);
      res.status(500).send("Internal Server Error");
    }
  }
  try {
    const output = template_neft(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/upi", async (req, res) => {
  if (!template_upi) {
    try {
      template_upi = handlebars.compile(
        readFileSync("public/upi.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_upi(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/imps", async (req, res) => {
  if (!template_imps) {
    try {
      template_imps = handlebars.compile(
        readFileSync("public/imps.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_imps(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/debit_card", async (req, res) => {
  if (!template_debit_card) {
    try {
      template_debit_card = handlebars.compile(
        readFileSync("public/debit_card.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_debit_card(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/recharge", async (req, res) => {
  if (!template_recharge) {
    try {
      template_recharge = handlebars.compile(
        readFileSync("public/recharge.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_recharge(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/electricity", async (req, res) => {
  if (!template_electricity) {
    try {
      template_electricity = handlebars.compile(
        readFileSync("public/electricity.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_electricity(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/insurance_premium", async (req, res) => {
  if (!template_insurance_premium) {
    try {
      template_insurance_premium = handlebars.compile(
        readFileSync("public/insurance_premium.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_insurance_premium(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/mutual_funds", async (req, res) => {
  if (!template_mutual_funds) {
    try {
      template_mutual_funds = handlebars.compile(
        readFileSync("public/mutual_funds.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_mutual_funds(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/ipo", async (req, res) => {
  if (!template_ipo) {
    try {
      template_ipo = handlebars.compile(
        readFileSync("public/ipo.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_ipo(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/stocks", async (req, res) => {
  if (!template_stocks) {
    try {
      template_stocks = handlebars.compile(
        readFileSync("public/stocks.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_stocks(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/current", async (req, res) => {
  if (!template_current) {
    try {
      template_current = handlebars.compile(
        readFileSync("public/current.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_current(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/salary", async (req, res) => {
  if (!template_salary) {
    try {
      template_salary = handlebars.compile(
        readFileSync("public/salary.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_salary(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/fixed_deposit", async (req, res) => {
  if (!template_fixed_deposit) {
    try {
      template_fixed_deposit = handlebars.compile(
        readFileSync("public/fixed_deposit.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_fixed_deposit(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/recurring_deposit", async (req, res) => {
  if (!template_recurring_deposit) {
    try {
      template_recurring_deposit = handlebars.compile(
        readFileSync("public/recurring_deposit.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_recurring_deposit(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/loans", async (req, res) => {
  if (!template_loans) {
    try {
      template_loans = handlebars.compile(
        readFileSync("public/loans.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_loans(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/saving/terms_and_condition", async (req, res) => {
  if (!template_saving_terms) {
    try {
      template_saving_terms = handlebars.compile(
        readFileSync("public/saving_terms_and_condition.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_saving_terms(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/calculator", async (req, res) => {
  if (!template_calculator) {
    try {
      template_calculator = handlebars.compile(
        readFileSync("public/calculator.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }

  try {
    const output = template_calculator(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/credit_card_tc", async (req, res) => {
  const filePath = path.join(__dirname, "public", "cymbal-credit-cards.pdf");

  try {
    res.setHeader("Content-Type", "application/pdf");
    res.status(200).sendFile(filePath);
  } catch (e) {
    handleError(e);
  }
});

app.get("/loans/terms_and_condition", async (req, res) => {
  if (!template_loan_tc) {
    try {
      template_loan_tc = handlebars.compile(
        readFileSync("public/loans_T&C.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_loan_tc(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

app.get("/loans/agreement", async (req, res) => {
  if (!template_loan_agreement) {
    try {
      template_loan_agreement = handlebars.compile(
        readFileSync("public/loan_agreement.html.hbs", "utf8"),
      );
    } catch (e) {
      handleError(e);
    }
  }
  try {
    const output = template_loan_agreement(data);
    res.status(200).send(output);
  } catch (e) {
    handleError(e);
  }
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(
    `Hello from Cloud Run! The container started successfully and is listening for HTTP requests on http://127.0.0.1:${PORT}`,
  );
});
