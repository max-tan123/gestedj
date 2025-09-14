// AI_DJ_Gestures jog mapping helper
// Decodes 7-bit two's complement relative values and applies Mixxx jog

var AI_DJ_GesturesJog = {};

AI_DJ_GesturesJog.decodeTwosComplement7 = function(value) {
    // 0x01..0x3F => +1..+63
    // 0x41..0x7F => -63..-1 (128 - v)
    // 0x00 or 0x40 => 0
    if (value === 0x00 || value === 0x40) {
        return 0;
    }
    if (value >= 0x01 && value <= 0x3F) {
        return value;
    }
    if (value >= 0x41 && value <= 0x7F) {
        return -(128 - value);
    }
    return 0;
};

AI_DJ_GesturesJog.scale = 0.08; // Tune sensitivity of each tick

AI_DJ_GesturesJog.jog = function(channel, control, value, status, group) {
    var delta = AI_DJ_GesturesJog.decodeTwosComplement7(value);
    if (delta === 0) {
        return;
    }
    var amount = delta * AI_DJ_GesturesJog.scale;
    engine.setValue(group, "jog", amount);
};


