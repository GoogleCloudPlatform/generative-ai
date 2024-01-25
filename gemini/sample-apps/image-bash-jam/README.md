# Testing Gemini from Bash

Note: I wrote an article on Medium which is very similar to this README :)

Link: <https://medium.com/@palladiusbonton/hey-gemini-explain-me-these-pictures-in-bash-06c03d0d0512>

Note: this code has been tested both locally and on Cloud Shell. For an easier authentication experience,
consider playing with this code on [Cloud Shell](https://cloud.google.com/shell/docs/using-cloud-shell).

## Setup

1. First lets download the repo and position ourself in the right directory:

```bash
cd
git clone  https://github.com/GoogleCloudPlatform/generative-ai
cd generative-ai/gemini/sample-apps/image-bash-jam/

# [optional] If you like a colored shell, do this. If not, scripts will detect its absence and will just print in shell default color (see `_lolcat` in `_common.sh`).
gem install lolcat
```

1. First check authentication. Make sure you login with gcloud (or whatever login you want to do) and set up the project_id correctly.

```bash
# If you're on Cloud Shell, you can skip this. You will authenticate with just a click.
gcloud auth login
```

If you have trouble with loggin in, you can use the following command to set the project_id (it also
supports local keys, check the docs on top of the file):

```bash
cp .envrc.dist .envrc
vim .envrc # Change PROJECT_ID and ACCOUNT with your project and email.
./01-setup.sh # sets up authentication, and includes `make images` to download resources locally.
```

## A simple test

1. Run the simplest script as a test:

`./gemini-why-is-the-sky-blue.sh`

Response:

```JSON
{
  "candidates": [
    {
      "content": {
        "role": "model",
        "parts": [
          {
            "text": "The sky is blue due to a phenomenon known as Rayleigh scattering. Here's the scientific explanation:\n\n1. Sunlight Composition: Sunlight, which is a form of electromagnetic radiation emitted by the sun, is composed of a spectrum of light waves of different wavelengths and colors. These colors include red, orange, yellow, green, blue, indigo, and violet, which together form the rainbow's spectrum.\n\n2. Scattering of Light: When sunlight enters the Earth's atmosphere, it interacts with molecules and particles present in the air, including nitrogen (N2) and oxygen (O2) molecules, as well as aerosols, dust, and other particles. These particles scatter the incoming sunlight in all directions.\n\n3. Rayleigh Scattering: The amount of scattering depends on the wavelength of light and the size of the particles. Shorter wavelengths of light, such as blue and violet, are scattered more efficiently than longer wavelengths like red and orange. This phenomenon, known as Rayleigh scattering, is named after Lord Rayleigh, who studied and explained it in the late 19th century.\n\n4. Scattering Intensity: The intensity of scattering is inversely proportional to the fourth power of the wavelength of light. This means that blue light with a shorter wavelength is scattered about 16 times more than red light with a longer wavelength.\n\n5. Blue Sky Appearance: As a result of Rayleigh scattering, the shorter-wavelength blue and violet colors are scattered more strongly by the molecules and particles in the atmosphere. When we look up at the sky, we primarily see the blue light that has been scattered in all directions by these particles, making the sky appear blue during the daytime.\n\n6. Color Variations: The scattering intensity can vary depending on the time of day, atmospheric conditions, and the amount of pollutants or particles in the air. At sunrise and sunset, when the sunlight has to travel through more of the atmosphere, more of the shorter wavelength light is scattered away, leaving the longer wavelength colors like red and orange to dominate, resulting in the colorful sky we see during those times.\n\n7. Blue Color Dominance: Although violet light has a slightly shorter wavelength than blue light, it is absorbed more by the Earth's atmosphere and by the ozone layer, which protects the Earth from harmful ultraviolet (UV) radiation. As a result, we primarily perceive the scattered blue light, making the sky appear blue to our eyes."
          }
        ]
      }
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 6,
    "candidatesTokenCount": 485,
    "totalTokenCount": 491
  }
}
```

Bingo! It tells you about Raileigh Scattering and also how much did you spend (491 tokens, should be less than 1 cent).

If this works, great, we can move into more interesting stuff!

## Hey Gemini, describe what you see

Let's start asking Gemini about images!

Let's start with one of my favouritest albums of all time: **Selling England by the pound**.

![Alt text](https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/img/genesis-selling-england.jpg "Genesis - Selling England by the pound (one of the best albums of all time!)")

```bash
./gemini-generic.sh images/genesis-selling-england.jpg Describe what you see
# 🤌  QUESTION: Describe what you see
# 🌡️ TEMPERATURE: 0.2
# 👀 Examining image images/genesis-selling-england.jpg: JPEG image data, JFIF standard 1.01, resolution (DPI), density 96x96, segment length 16, baseline, precision 8, 536x528, components 3.
# ♊ Gemini no Saga answer for you:
The cover of Genesis' album Selling England by the Pound features a painting by British artist Paul Whitehead. The painting depicts a group of people in a park, with a man sleeping on a bench in the foreground. The people are all wearing clothes from the 1920s or 1930s, and the painting has a nostalgic, almost surreal feel to it. The colors are muted and the figures are slightly blurred, which gives the painting a dreamlike quality. The painting is also full of symbolism, with the sleeping man representing England and the people around him representing the different aspects of English society. The painting has been interpreted in many different ways, but it is generally seen as a commentary on the state of England in the 1970s.
```

A quick googling confirms that <https://en.wikipedia.org/wiki/Paul_Whitehead> actually covered one of my favourite album of all times. If you love Genesis too and want to see me play Firth of Fifth, please check <https://www.youtube.com/watch?v=4VBxd9n1dSU>.

**Note**: should the script fail, make sure that `images/genesis-selling-england.jpg` exists (or re-issue `make images`) and that authentication worked (check `.tmp*` files for more verbose output).

## Let's compare TWO images

Since we're celebrating Gemini launch and I'm a huge fan of the Saint Seiya manga/anime, I've asked Gemini to compare two things close to him:

<table align=center >
  <tr  valign=top >
    <td valign=top >
        Gemini constellation
    </td>
    <td  valign=top>
        Gemini Saint (Saga) from Saint Seiya
    </td>
  </tr>
  <tr  valign=top >
    <td valign=top >
        <img src="https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/img/gemini-constellation.png"  alt="Gemini constellation" width=360px >
    </td>
    <td  valign=top>
        <img src="https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/img/saga-blue-hair.jpg" alt="Gemini no-saga with blue hair" width=360px >
    </td>
  </tr>
</table>

```bash
$ make compare-two-geminis
$ ./gemini-generic-two-pics.sh  images/gemini-constellation.png   images/saga-blue-hair.jpg
♊️ Question: Can you highlight similarity and differences between the two? Also, do you recognize the same person in both of them?
 👀 Examining image1 images/gemini-constellation.png: images/gemini-constellation.png: PNG image data, 1675 x 1302, 8-bit/color RGBA, non-interlaced.
 👀 Examining image2 images/saga-blue-hair.jpg: images/saga-blue-hair.jpg: JPEG image data, JFIF standard 1.01, aspect ratio, density 1x1, segment length 16, baseline, precision 8, 193x261, components 3.
♊️ Describing attached image:
 The two images are of the constellation Gemini and the anime character Gemini Saga. The constellation is said to represent the twins Castor and Pollux, while the character Gemini Saga is a Gemini Saint in the anime series Saint Seiya. Both images depict two figures that are connected to each other. The constellation is made up of stars, while the character is a human.
```

Well done Gemini! *Know thyself*, Socrates would say.
Note that the images are a PNG and a JPG - nothing can stop Gemini from comparing them!

## Introducing Audio

Why don't we throw some audio in the mix?

My `./tts.sh` creates an MP3 out of an english (or Italian!) text given in ARGV. Convenient uh?

```bash
$ make age-test
# => equivalent to:
$ GENERATE_MP3=true ./gemini-generic.sh images/ricc-family-with-santa.jpg Tell me the age of the people you see, from left to right.
# 🤌  QUESTION: Tell me the age of the people you see, from left to right.
# 🌡️  TEMPERATURE: 0.2
# 👀 Examining image images/ricc-family-with-santa.jpg: JPEG image data, JFIF standard 1.01, aspect ratio, density 1x1, segment length 16, Exif Standard: [TIFF image data, little-endian, direntries=3, software=Google], baseline, precision 8, 1164x826, components 3.
# ♊ Gemini no Saga answer for you:
1. 30-35
2. 2-3
3. 40-45
4. 2-3
5. 60-65
[..]
All good. MP3 created [..]
```

Now, interestingly it also creates an MP3 of the answer. Not super interesting with all thes enumbers, but might be
nice to see it for longer verbose answers. You can hear it by opening the file under `output/` folder.
(<a href="https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/mp3/ricc-family-with-santa.jpg.mp3" >images/mp3/ricc-family-with-santa.jpg.mp3</a>).

### Troubleshooting

Sometimes you might have authentication warnings (partiocularly with the text-to-speech API).
You can fix it by re-authenticating through ADC:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$PROJECT_ID"
```

Another way is to download a key and put it under `private/YOUR_PROJECT_ID.json`.

The script `01-setup.sh` has some magic built in, and will pick it up automagically and log in through it :)

More info here: <https://cloud.google.com/docs/authentication/troubleshoot-adc#user-creds-client-based>

## An italian image, explained in Italian

How about we do the same, but spice it up a bit with italian text and sound?

![Alt text](https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/img/italian-town.jpg "Photo of Trento City")

```bash
./gemini-explain-image.sh images/italian-town.jpg
# 🤌  QUESTION: Describe what you see
# 🌡️  TEMPERATURE: 0.2
# 👀 Examining image: JPEG image data, JFIF standard 1.01, aspect ratio, density 1x1, segment length 16, Exif Standard: [TIFF image data, little-endian, direntries=1, software=Google], baseline, precision 8, 926x1230, components 3.
# ♊ Gemini no Saga answer for you:
 This is a view of the city of Trento, Italy from the Buonconsiglio Castle.
```

This is good! I didn't know the photographer was shooting from the Buonconsiglio Castle. Awesome. But it's in English.

```bash
$ GENERATE_MP3=true ./gemini-explain-image-italian.sh images/italian-town.jpg
# 🤌  QUESTION: Descrivimi cosa vedi in questa immagine
# 🌡️  TEMPERATURE: 0.2
# 👀 Examining image images/italian-town.jpg: JPEG image data, JFIF standard 1.01, aspect ratio, density 1x1, segment length 16, Exif Standard: [TIFF image data, little-endian, direntries=1, software=Google], baseline, precision 8, 926x1230, components 3.
# ♊ Gemini no Saga answer for you:
 La foto mostra una loggia con delle colonne in pietra che incorniciano la vista di una città.
 La città è circondata da montagne e si possono vedere i tetti delle case e le torri delle chiese.
 Il cielo è azzurro e ci sono delle nuvole bianche.
# TTS_LANG: it-IT
Written .tmp.tts-output.json. curl_ret=0
t.audio.encoded: ASCII text, with very long lines (65536), with no line terminators
t.mp3:           MPEG ADTS, layer III, v2,  32 kbps, 24 kHz, Monaural
t.mp3: MPEG ADTS, layer III, v2,  32 kbps, 24 kHz, Monaural
All good. MP3 created: 't.La foto mostra una loggia con delle colonne in pie.mp3'
```

As you see, italian is more verbose and it knows more about Trento, but it's not aware of the *Buonconsiglio Palace*.
Interesting! I presume the Italian model has less training material to learn from than the English one. Makes sense.

Btw, I highly recommend Trento, I was cycling around there: great views and great wines!

Now, to create the Italian MP3, I had to hardcode the type of audio I wanted into `TTS_LANG: it-IT`.
This is the only added value to the `./gemini-explain-image-italian.sh` script so you should be able
to adapt seamlessly to your favorite language. TextToSpeech API supports nearly 200 of them!

The MP3 result is conveniently copied under [🇮🇹 images/mp3/italian-town.jpg.mp3](https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/mp3/italian-town.jpg.mp3).

## Something useful now: understand a diagram

I have a headset at work which is amazing, but I'm never sure how to turn it on or off; if I get it from charge its automatically on for me, but what if I forgot it non charging last night? This is what happened to me this morning.

Gemini to the rescue!

1. Google "Accrux ear phone user manual and get PDF". => `images/instruction-manuals/Acrux-User-Manual-4700503.pdf`
2. Since Gemini doesn't read PDFs (yet) from UI, here's the PNG: <a href="https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/instruction-manuals/Acrux-User-Manual-4700503.png" >images/instruction-manuals/Acrux-User-Manual-4700503.png</a>.
3. This was the hard part. Let's now ask questions. There are three as I used the UI:

![Alt text](cloudconsole-screenshot.png?raw=true "Riccardo using DevConsole to ask Gemini with a click")

1. Let's do the same from CLI:

```bash
$ make read-instruction-manual-for-me
[..]
./gemini-generic.sh images/instruction-manuals/Acrux-User-Manual-4700503.png '1. How do i TURN it on? 2. Where is the power button located? 3. Is this the one called ANC?'
# 🤌  QUESTION: 1. How do i TURN it on? 2. Where is the power button located? 3. Is this the one called ANC?
# 🌡️  TEMPERATURE: 0.2
# 👀 Examining image images/instruction-manuals/Acrux-User-Manual-4700503.png: PNG image data, 1664 x 929, 8-bit/color RGBA, non-interlaced.
# ♊ Gemini no Saga answer for you:
1. Long press the power button for 2 seconds.
2. The power button is located on the right earcup.
3. Yes, this is the one called ANC.
# Note: No mp3 file generated (use GENERATE_MP3=true to generate one)
```

There you go, the button IS the ANC button, I thought so! Thanks Gemini!

## An unexpected Games of Thrones plot twist

This is the avatar I use in Google. I randomly asked this:

![Alt text](https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/img/ricc-logo.png "Riccardo GCP logo - taken in the Amsterdam office")

```bash
$ ./gemini-explain-image.sh images/ricc-logo.png
[..]
This is a photo of a man standing behind a Google Cloud Platform cutout.
The man is smiling and wearing a shirt that says, “That’s what I do,
I drink and I know things.” The background is a brick wall with blue
and white accents.
```

And I thought! Of course, this is my favourite Games of Thrones tshirt.

Let’s ask Gemini:

```bash
$ GENERATE_MP3=true ./gemini-generic.sh images/ricc-logo.png Do you recognize the quote in this person tshirt
[..]
 "That's what I do, I drink and I know things" is a quote from the TV show Game of Thrones,
 said by the character Tyrion Lannister.
```

* MP3: <a href='https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/mp3/ricc-logo.png.mp3' >images/mp3/ricc-logo.png.mp3</a> (I don't think
  GitHub supports playing this audio - but you can download it and hear it).

* <audio controls="controls">
  <source type="audio/mp3" src="https://storage.googleapis.com/github-repo/use-cases/image-bash-jam/mp3/ricc-logo.png.mp3"></source>
  <p>🔇 Sorry, Your browser or GitHub markdown does not support the audio element.</p>
  </audio>

* Response: “ "That's what I do, I drink and I know things" is a quote from the TV show
  Game of Thrones, said by the character Tyrion Lannister.”

Wow: *Chapeau*, Gemini!
