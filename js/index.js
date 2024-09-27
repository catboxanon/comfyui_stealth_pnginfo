import { app } from "../../scripts/app.js";

// https://gist.github.com/catboxanon/ca46eb79ce55e3216aecab49d5c7a3fb
function imageHasAlpha(context, canvas) {
  var data = context.getImageData(0, 0, canvas.width, canvas.height).data,
    hasAlphaPixels = false;
  for (var i = 3, n = data.length; i < n; i += 4) {
    if (data[i] < 255) {
      hasAlphaPixels = true;
      break;
    }
  }
  return hasAlphaPixels;
}

function readInfoFromImageStealth(image) {
  let geninfo, items, paramLen;
  let r, g, b, a;

  const canvas = document.createElement("canvas");

  // trying to read stealth pnginfo
  const [width, height] = [image.width, image.height];
  const context = canvas.getContext("2d");
  canvas.width = image.width;
  canvas.height = image.height;
  context.drawImage(image, 0, 0);

  const imageData = context.getImageData(0, 0, width, height);
  const data = imageData.data;

  let hasAlpha = imageHasAlpha(context, canvas);
  let mode = null;
  let compressed = false;
  let binaryData = "";
  let bufferA = "";
  let bufferRGB = "";
  let indexA = 0;
  let indexRGB = 0;
  let sigConfirmed = false;
  let confirmingSignature = true;
  let readingParamLen = false;
  let readingParam = false;
  let readEnd = false;

  for (let x = 0; x < width; x++) {
    for (let y = 0; y < height; y++) {
      let i = (y * width + x) * 4;

      if (hasAlpha) {
        [r, g, b, a] = data.slice(i, i + 4);
        bufferA += (a & 1).toString();
        indexA++;
      } else {
        [r, g, b] = data.slice(i, i + 3);
      }
      bufferRGB += (r & 1).toString();
      bufferRGB += (g & 1).toString();
      bufferRGB += (b & 1).toString();
      indexRGB += 3;

      if (confirmingSignature) {
        if (indexA === "stealth_pnginfo".length * 8) {
          const decodedSig = new TextDecoder().decode(
            new Uint8Array(bufferA.match(/\d{8}/g).map((b) => parseInt(b, 2)))
          );
          if (
            decodedSig === "stealth_pnginfo" ||
            decodedSig === "stealth_pngcomp"
          ) {
            confirmingSignature = false;
            sigConfirmed = true;
            readingParamLen = true;
            mode = "alpha";
            if (decodedSig === "stealth_pngcomp") {
              compressed = true;
            }
            bufferA = "";
            indexA = 0;
          } else {
            readEnd = true;
            break;
          }
        } else if (indexRGB === "stealth_pnginfo".length * 8) {
          const decodedSig = new TextDecoder().decode(
            new Uint8Array(bufferRGB.match(/\d{8}/g).map((b) => parseInt(b, 2)))
          );
          if (
            decodedSig === "stealth_rgbinfo" ||
            decodedSig === "stealth_rgbcomp"
          ) {
            confirmingSignature = false;
            sigConfirmed = true;
            readingParamLen = true;
            mode = "rgb";
            if (decodedSig === "stealth_rgbcomp") {
              compressed = true;
            }
            bufferRGB = "";
            indexRGB = 0;
          }
        }
      } else if (readingParamLen) {
        if (mode === "alpha" && indexA === 32) {
          paramLen = parseInt(bufferA, 2);
          readingParamLen = false;
          readingParam = true;
          bufferA = "";
          indexA = 0;
        } else if (mode != "alpha" && indexRGB === 33) {
          paramLen = parseInt(bufferRGB.slice(0, -1), 2);
          readingParamLen = false;
          readingParam = true;
          bufferRGB = bufferRGB.slice(-1);
          indexRGB = 1;
        }
      } else if (readingParam) {
        if (mode === "alpha" && indexA === paramLen) {
          binaryData = bufferA;
          readEnd = true;
          break;
        } else if (mode != "alpha" && indexRGB >= paramLen) {
          const diff = paramLen - indexRGB;
          if (diff < 0) {
            bufferRGB = bufferRGB.slice(0, diff);
          }
          binaryData = bufferRGB;
          readEnd = true;
          break;
        }
      } else {
        // Impossible
        readEnd = true;
        break;
      }
    }

    if (readEnd) {
      break;
    }
  }

  if (sigConfirmed && binaryData) {
    // Convert binary string to UTF-8 encoded text
    const byteData = new Uint8Array(
      binaryData.match(/\d{8}/g).map((b) => parseInt(b, 2))
    );
    let decodedData;
    if (compressed) {
      decodedData = pako.inflate(byteData, { to: "string" });
    } else {
      decodedData = new TextDecoder().decode(byteData);
    }
    geninfo = decodedData;
  }

  return geninfo;
}

function clearUnableToFindWorkflowModal() {
  // If there's a proper way to prevent this modal from showing up at all, please let me know
  const modals = document.querySelectorAll(".comfy-modal");
  modals.forEach((modal) => {
    if (modal.textContent.includes("Unable to find workflow")) {
      modal.remove();
    }
  });
}

app.registerExtension({
  name: "comfyui_stealth_pnginfo",
  async init() {
    // Modification of upstream code to handle stealth metadata
    // https://github.com/Comfy-Org/ComfyUI_frontend/blob/8d7693e5adf1ef5475c636a697c3e1baeb29451d/src/scripts/app.ts#L1001
    // https://github.com/Comfy-Org/ComfyUI_frontend/blob/8d7693e5adf1ef5475c636a697c3e1baeb29451d/src/scripts/app.ts#L2686
    document.addEventListener("drop", async (evt) => {
      evt.preventDefault();

      const n = app.dragOverNode;
      app.dragOverNode = null;
      // Node handles file drop, we dont use the built in onDropFile handler as its buggy
      // If you drag multiple files it will call it multiple times with the same file
      // @ts-expect-error This is not a standard event. TODO fix it.
      if (n && n.onDragDrop && (await n.onDragDrop(evt))) {
        return;
      }
      if (
        evt.dataTransfer.files.length &&
        evt.dataTransfer.files[0].type === "image/png"
      ) {
        let file = evt.dataTransfer.files[0];
        const removeExt = (f) => {
          if (!f) return f;
          const p = f.lastIndexOf(".");
          if (p === -1) return f;
          return f.substring(0, p);
        };
        const fileName = removeExt(file.name);
        const img = new Image();
        img.src = URL.createObjectURL(file);
        img.onload = async () => {
          evt.stopPropagation();
          const info = readInfoFromImageStealth(img);
          try {
            if (info) {
              const pngInfo = JSON.parse(info);
              if (pngInfo?.workflow) {
                await app.loadGraphData(
                  JSON.parse(pngInfo.workflow),
                  true,
                  true,
                  fileName
                );
                clearUnableToFindWorkflowModal();
              } else if (pngInfo?.prompt) {
                app.loadApiJson(JSON.parse(pngInfo.prompt), fileName);
                clearUnableToFindWorkflowModal();
              } else if (pngInfo?.parameters) {
                app.changeWorkflow(() => {
                  importA1111(app.graph, pngInfo.parameters);
                }, fileName);
                clearUnableToFindWorkflowModal();
              }
            }
          } catch (err) {
            console.error("Error reading stealth pnginfo: ", err);
          }
        };
      }
    });
  },
});