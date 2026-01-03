import "./index.css";
import { Composition } from "remotion";
import { McnComposition } from "./McnComposition";
import timelineData from "./timeline.json";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="McnMain"
        component={McnComposition}
        durationInFrames={timelineData.durationInFrames}
        fps={timelineData.fps}
        width={timelineData.width}
        height={timelineData.height}
      />
    </>
  );
};
