// Ενδεικτική λύση για την καρτέλα JavaScript του MakeCode.
basic.showLeds(`
    . . . . .
    . # . # .
    . . . . .
    # . . . #
    . # # # .
`)
input.onButtonPressed(Button.A, function () {
    basic.showLeds(`
        . . . . .
        . # . # .
        . . . . .
        # . . . #
        . # # # .
    `)
})
input.onButtonPressed(Button.B, function () {
    basic.showLeds(`
        . . . . .
        . # . # .
        . . . . .
        . # # # .
        # . . . #
    `)
})
input.onButtonPressed(Button.AB, function () {
    basic.showLeds(`
        . # . # .
        # # # # #
        # # # # #
        . # # # .
        . . # . .
    `)
})
