export const environment = {
  firebase: {
    apiKey: '<your API Key>',
    authDomain: '<your Auth Domain>',
    projectId: '<your Project ID>',
  },
  // The requiredLogin needs to be set always to True to ensure 
  // the user's picture is taken always by default the first time
  requiredLogin: 'True',
  backendURL: 'http://localhost:8080/api',
  chatbotName: 'LinkedIn Profile Image Generation Agent',
};
