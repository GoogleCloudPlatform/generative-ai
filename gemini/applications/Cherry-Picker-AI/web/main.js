import { callGemini } from './gemini-api.js';

let form = document.querySelector('form');
let output = document.querySelector('.output');

var user_photo_base64 = 'user_selected_photo';

const fileInput = document.getElementById('imageInput');
const previewImage = document.getElementById('user_preview');

fileInput.addEventListener('change', (event) => {
  const file = event.target.files[0];
  const reader = new FileReader();
  reader.readAsDataURL(file);

  reader.onload = function (e) {
    console.log("Image was loaded to screen")
    previewImage.src = e.target.result;
    user_photo_base64 = reader.result.replace('data:', '').replace(/^.+,/, '')
    //console.log(user_photo_base64)
  };

});


document.getElementById("cristianThySavior").onclick=async() => {
  await testMarketing();
};

async function testMarketing() {
  try {
    const response = await fetch('/api/request_marketing', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        'filename': 'Cherry.png'
      })
    })
    .then(response => response.json())
    .then(data => {
      console.log(data); // Log the entire response object
    })
    .catch(error => console.error('Error:', error));

  } catch (error) {
    console.error('Error:', error);
  }
}


form.onsubmit = async (ev) => {
  ev.preventDefault();
  output.textContent = 'Sent to the Backend...';

  const fileInput = document.getElementById('imageInput');
  const file = fileInput.files[0];
  console.log(file)
  
  const formData = new FormData();
  formData.append('file', file); // Add the file to the FormData object


  fetch('/api/start_receiver', { 
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    console.log('Response:', data); 

    if (data.hasOwnProperty("single_produce_rating")){
      console.log("Single Produce Rating Returned!")
      // console.log(JSON.parse(data.single_produce_rating)["Absence of Defects Rating"])
      var inner_data = JSON.parse(data.single_produce_rating)

      let formattedString = 
  '<h3>Produce Rating</h3>' + 
  '<p>' + 
  '<b>Overall Rating:</b> ' + inner_data["Overall Rating"] + '<br>' +
  '<b>Quality Rating:</b> ' + inner_data["Quality Rating"] + '<br>' +
  '<b>Freshness Rating:</b> ' + inner_data["Freshness Rating"] + '<br>' +
  '<b>Absence of Defects Rating:</b> ' + inner_data["Absence of Defects Rating"] + '<br>' +
  '<b>Reasoning:</b> ' + inner_data["Reasoning for Rating"] + '<br>' +
  '<b>Pros:</b><br>' +
  '<ul>' +
  '<li>There are pros.. takes too long for me to figure out how to display tbh..</li>' +
  '</ul>' +
  '<b>Cons:</b><br>' +
  '<ul>' +
  '<li>There are cons.. takes too long for me to figure out how to display tbh..</li>' + 
  '</ul>' +
  '</p>';
      //const parsedInnerJson = JSON.parse(data.single_produce_rating)
      output.innerHTML = formattedString //JSON.stringify(parsedInnerJson, null, 2)
    } 
    else if (data.hasOwnProperty("bulk_produce_selector")) {
      console.log("Bulk Produce Selector Returned!")
      output.textContent = JSON.stringify(data["bulk_produce_selector"])
    } 
    else
    output.textContent = JSON.stringify(data)

  })
  .catch(error => {
    console.error('Error:', error);
    // Handle errors (e.g., display an error message)
  });
};