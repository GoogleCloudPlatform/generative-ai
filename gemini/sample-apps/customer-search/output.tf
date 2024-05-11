########[start]cloud function urls####################
output "account-health-summarisation-optimised_url" {
  value = google_cloudfunctions2_function.account-health-summarisation-optimised.url
}

output "account-health-tips_url" {
  value = google_cloudfunctions2_function.account-health-tips.url
}

output "check-cust-id-in-database_url" {
  value = google_cloudfunctions2_function.check-cust-id-in-database.url
}

output "create_fd_url" {
  value = google_cloudfunctions2_function.create_fd.url
}

output "event-recommendationv2_url" {
  value = google_cloudfunctions2_function.event-recommendationv2.url
}

output "event-recommendationv3_url" {
  value = google_cloudfunctions2_function.event-recommendationv3.url
}

output "expense-predictionv2_url" {
  value = google_cloudfunctions2_function.expense-predictionv2.url
}

output "extend-overdraft_url" {
  value = google_cloudfunctions2_function.extend-overdraft.url
}

output "fd_confirmation_url" {
  value = google_cloudfunctions2_function.fd_confirmation.url
}

output "fd_recommendation_url" {
  value = google_cloudfunctions2_function.fd_recommendation.url
}

output "fd_tenure_url" {
  value = google_cloudfunctions2_function.fd_tenure.url
}

output "find_nearest_bike_dealer_url" {
  value = google_cloudfunctions2_function.find_nearest_bike_dealer.url
}

output "find_nearest_car_dealers_url" {
  value = google_cloudfunctions2_function.find_nearest_car_dealers.url
}

output "fixed-deposit-recommendation_url" {
  value = google_cloudfunctions2_function.fixed-deposit-recommendation.url
}

output "get-account-balance_url" {
  value = google_cloudfunctions2_function.get-account-balance.url
}

output "get_anomaly_transaction_url" {
  value = google_cloudfunctions2_function.get_anomaly_transaction.url
}

output "get_category_wise_expenditure_url" {
  value = google_cloudfunctions2_function.get_category_wise_expenditure.url
}

output "get_return_of_investment_url" {
  value = google_cloudfunctions2_function.get_return_of_investment.url
}

output "get_travel_dates_url" {
  value = google_cloudfunctions2_function.get_travel_dates.url
}

output "high_risk_mutual_funds_url" {
  value = google_cloudfunctions2_function.high_risk_mutual_funds.url
}

output "how_my_debt_funds_doing_url" {
  value = google_cloudfunctions2_function.how_my_debt_funds_doing.url
}

output "how_my_mutual_fund_doing_url" {
  value = google_cloudfunctions2_function.how_my_mutual_fund_doing.url
}

output "is_in_india_url" {
  value = google_cloudfunctions2_function.is_in_india.url
}

output "set_destination_url" {
  value = google_cloudfunctions2_function.set_destination.url
}

output "set_fd_amount_url" {
  value = google_cloudfunctions2_function.set_fd_amount.url
}

output "rag_qa_chain_2_url" {
  value = google_cloudfunctions2_function.rag_qa_chain_2.url
}

output "recommend_debt_funds_url" {
  value = google_cloudfunctions2_function.recommend_debt_funds.url
}

output "recommend_mutual_fund_url" {
  value = google_cloudfunctions2_function.recommend_mutual_fund.url
}

output "tenure_validation_url" {
  value = google_cloudfunctions2_function.tenure_validation.url
}

output "travel_card_recommendation_url" {
  value = google_cloudfunctions2_function.travel_card_recommendation.url
}

output "unusual_spends_url" {
  value = google_cloudfunctions2_function.unusual_spends.url
}

output "upload_credit_card_url" {
  value = google_cloudfunctions2_function.upload_credit_card.url
}

output "translation-handler-cymbal-bank_url" {
  value = google_cloudfunctions2_function.translation-handler-cymbal-bank.url
}

output "credit-card-imagen_url" {
  value = google_cloudfunctions2_function.credit-card-imagen.url
}

output "user-login_url" {
  value = google_cloudfunctions2_function.user-login.url
}

output "translate_url" {
  value = google_cloudfunctions2_function.translate.url
}
########[end]cf urls####################

# artifact registry repo for uploading website container image
output "website_repo_name" {
  value = google_artifact_registry_repository.website-repo.name
}