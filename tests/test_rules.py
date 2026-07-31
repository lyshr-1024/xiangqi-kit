"""走法生成规则测试：每条易错规则一个手工构造局面。"""
from xiangqi import Position, sq


def targets_from(pos: Position, square: int) -> set:
    return {to for frm, to in pos.legal_moves() if frm == square}


def test_horse_free_has_eight_moves():
    pos = Position.from_fen("3k5/9/9/9/9/4N4/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(5, 4)) == {
        sq(3, 3), sq(3, 5), sq(4, 2), sq(4, 6),
        sq(6, 2), sq(6, 6), sq(7, 3), sq(7, 5),
    }


def test_horse_leg_blocked():
    # (4,4) 蹩住马腿，向上两格的两个落点被排除
    pos = Position.from_fen("3k5/9/9/9/4p4/4N4/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(5, 4)) == {
        sq(4, 2), sq(4, 6), sq(6, 2), sq(6, 6), sq(7, 3), sq(7, 5),
    }


def test_elephant_free_moves():
    pos = Position.from_fen("3k5/9/9/9/9/9/9/4B4/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(7, 4)) == {sq(5, 2), sq(5, 6), sq(9, 2), sq(9, 6)}


def test_elephant_eye_blocked():
    # (6,3) 塞象眼，挡住去 (5,2) 的路
    pos = Position.from_fen("3k5/9/9/9/9/9/3p5/4B4/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(7, 4)) == {sq(5, 6), sq(9, 2), sq(9, 6)}


def test_elephant_cannot_cross_river():
    pos = Position.from_fen("3k5/9/9/9/9/2B6/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(5, 2)) == {sq(7, 0), sq(7, 4)}


def test_cannon_moves_and_screen_capture():
    # 炮(5,0)，己方兵(5,3)作炮架，可隔子吃 r(5,6)，不可吃 p(5,8)（隔两子）
    pos = Position.from_fen("3k5/9/9/9/9/C2P2r1p/9/9/9/5K3 w - - 0 1")
    vertical = {sq(r, 0) for r in range(10) if r != 5}
    assert targets_from(pos, sq(5, 0)) == {sq(5, 1), sq(5, 2), sq(5, 6)} | vertical


def test_flying_general_pins_screen_piece():
    # 双将同线，中间只有红炮：炮横走会照面，纵走保持遮挡
    pos = Position.from_fen("4k4/9/9/9/9/4C4/9/9/9/4K4 w - - 0 1")
    assert targets_from(pos, sq(5, 4)) == {sq(r, 4) for r in (1, 2, 3, 4, 6, 7, 8)}


def test_king_cannot_step_into_facing():
    pos = Position.from_fen("4k4/9/9/9/9/9/9/9/9/3K5 w - - 0 1")
    assert targets_from(pos, sq(9, 3)) == {sq(8, 3)}


def test_pawn_before_river_only_forward():
    pos = Position.from_fen("3k5/9/9/9/9/4P4/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(5, 4)) == {sq(4, 4)}


def test_pawn_after_river_can_go_sideways_not_back():
    pos = Position.from_fen("3k5/9/9/9/4P4/9/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(4, 4)) == {sq(3, 4), sq(4, 3), sq(4, 5)}


def test_pawn_on_last_rank_only_sideways():
    pos = Position.from_fen("P2k5/9/9/9/9/9/9/9/9/5K3 w - - 0 1")
    assert targets_from(pos, sq(0, 0)) == {sq(0, 1)}


def test_black_pawn_moves_down():
    pos = Position.from_fen("3k5/9/9/9/9/4p4/9/9/9/5K3 b - - 0 1")
    assert targets_from(pos, sq(5, 4)) == {sq(6, 4), sq(5, 3), sq(5, 5)}


def test_advisor_center_and_corner():
    pos = Position.from_fen("3k5/9/9/9/9/9/9/9/4A4/4K4 w - - 0 1")
    assert targets_from(pos, sq(8, 4)) == {sq(7, 3), sq(7, 5), sq(9, 3), sq(9, 5)}
    pos = Position.from_fen("3k5/9/9/9/9/9/9/9/9/3AK4 w - - 0 1")
    assert targets_from(pos, sq(9, 3)) == {sq(8, 4)}


def test_king_confined_to_palace():
    # (4,4) 黑卒挡在两王之间，四个方向都合法且不越出九宫
    pos = Position.from_fen("4k4/9/9/9/4p4/9/9/9/4K4/9 w - - 0 1")
    assert targets_from(pos, sq(8, 4)) == {sq(7, 4), sq(9, 4), sq(8, 3), sq(8, 5)}


def test_in_check_and_escape():
    # 红车(5,4)将军；(0,3) 因照面红帅(9,3)不可去，(1,4) 仍被车攻击
    pos = Position.from_fen("4k4/9/9/9/9/4R4/9/9/9/3K5 b - - 0 1")
    assert pos.in_check()
    assert pos.legal_moves() == [(sq(0, 4), sq(0, 5))]


def test_checkmate():
    # 车(0,8)将军，(0,3)照面、(0,5)被同车攻击、(1,4)被车(1,0)攻击
    pos = Position.from_fen("4k3R/R8/9/9/9/9/9/9/9/3K5 b - - 0 1")
    assert pos.in_check()
    assert pos.legal_moves() == []
    assert pos.is_checkmate()
    assert not pos.is_stalemate()


def test_stalemate_is_loss_condition():
    # 困毙：黑将无子可动但未被将军
    pos = Position.from_fen("4k4/3R1R3/9/9/9/9/9/9/9/3K5 b - - 0 1")
    assert not pos.in_check()
    assert pos.legal_moves() == []
    assert pos.is_stalemate()
    assert not pos.is_checkmate()


def test_make_unmake_roundtrip():
    pos = Position.from_fen("3k5/9/9/9/9/C2P2r1p/9/9/9/5K3 w - - 0 1")
    fen = pos.to_fen()
    for mv in pos.legal_moves():
        undo = pos.make_move(mv)
        pos.unmake_move(undo)
        assert pos.to_fen() == fen
