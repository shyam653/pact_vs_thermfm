package chipyard

import org.chipsalliance.cde.config.Config

/** IP1's two Rocket tiles and memory hierarchy, plus the pinned MMIO FFT. */
class DualRocketFFTConfig extends Config(
  new fftgenerator.WithFFTGenerator(
    baseAddr = 0x2400, numPoints = 8, width = 16, decPt = 8) ++
  new freechips.rocketchip.rocket.WithNHugeCores(2) ++
  new chipyard.config.AbstractConfig)
