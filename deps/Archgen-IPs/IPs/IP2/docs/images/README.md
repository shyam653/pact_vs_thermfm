# Block diagram

`block-diagram.png` depicts the generated `DualRocketFFTConfig` architecture.
Orange highlights the FFT additions relative to IP1. Connections are a simplified
architectural view, not a signal-level wiring diagram or physical floorplan.
The FFT's actual data path is input deserializer → FFT → reorder → output registers;
the bidirectional diagram connectors summarize connectivity.

The image was produced using the built-in image generation tool, with the prompt
in `prompt.txt`, and checked against the generated memory map and source hierarchy.
