import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { PHONE_ROLES, useMe, type Me } from "./auth/useMe";
import { AppShell } from "./layout/AppShell";
import { PhoneShell } from "./layout/PhoneShell";
import { Login } from "./pages/Login";
import { Skeleton } from "./ui/Skeleton";

const Home = lazy(() => import("./pages/Home").then((m) => ({ default: m.Home })));
const Roster = lazy(() => import("./pages/Roster").then((m) => ({ default: m.Roster })));
const AssignmentBuild = lazy(() => import("./pages/AssignmentBuild").then((m) => ({ default: m.AssignmentBuild })));
const Swaps = lazy(() => import("./pages/Swaps").then((m) => ({ default: m.Swaps })));
const Permits = lazy(() => import("./pages/Permits").then((m) => ({ default: m.Permits })));
const PermitDetail = lazy(() => import("./pages/PermitDetail").then((m) => ({ default: m.PermitDetail })));
const Warnings = lazy(() => import("./pages/Warnings").then((m) => ({ default: m.Warnings })));
const WarningRecord = lazy(() => import("./pages/WarningRecord").then((m) => ({ default: m.WarningRecord })));
const District = lazy(() => import("./pages/District").then((m) => ({ default: m.District })));
const Reports = lazy(() => import("./pages/Reports").then((m) => ({ default: m.Reports })));
const ReportDetail = lazy(() => import("./pages/ReportDetail").then((m) => ({ default: m.ReportDetail })));
const Inspections = lazy(() => import("./pages/Inspections").then((m) => ({ default: m.Inspections })));
const Actions = lazy(() => import("./pages/Actions").then((m) => ({ default: m.Actions })));
const Learning = lazy(() => import("./pages/Learning").then((m) => ({ default: m.Learning })));
const Activities = lazy(() => import("./pages/Activities").then((m) => ({ default: m.Activities })));
const ActivityDetail = lazy(() => import("./pages/ActivityDetail").then((m) => ({ default: m.ActivityDetail })));
const Groups = lazy(() => import("./pages/Groups").then((m) => ({ default: m.Groups })));
const Screening = lazy(() => import("./pages/Screening").then((m) => ({ default: m.Screening })));
const WorkerHealth = lazy(() => import("./pages/WorkerHealth").then((m) => ({ default: m.WorkerHealth })));
const Validation = lazy(() => import("./pages/Validation").then((m) => ({ default: m.Validation })));
const Impact = lazy(() => import("./pages/Impact").then((m) => ({ default: m.Impact })));
const Governance = lazy(() => import("./pages/Governance").then((m) => ({ default: m.Governance })));
const Audit = lazy(() => import("./pages/Audit").then((m) => ({ default: m.Audit })));
const Signals = lazy(() => import("./pages/Signals").then((m) => ({ default: m.Signals })));
const People = lazy(() => import("./pages/admin/People").then((m) => ({ default: m.People })));
const SiteClock = lazy(() => import("./pages/admin/SiteClock").then((m) => ({ default: m.SiteClock })));
const WorkerHome = lazy(() => import("./pages/phone/WorkerHome").then((m) => ({ default: m.WorkerHome })));
const ForemanHome = lazy(() => import("./pages/phone/ForemanHome").then((m) => ({ default: m.ForemanHome })));
const PhoneReport = lazy(() => import("./pages/phone/PhoneReport").then((m) => ({ default: m.PhoneReport })));
const Cards = lazy(() => import("./pages/phone/Cards").then((m) => ({ default: m.Cards })));


function Loading() {
  return (
    <div style={{ padding: 32, maxWidth: 960 }}>
      <Skeleton lines={6} />
    </div>
  );
}

function Signed({ children, phone }: { children: (me: Me) => ReactNode; phone?: boolean }) {
  const me = useMe();
  const location = useLocation();
  if (me.isPending) return <Loading />;
  if (me.isError || !me.data) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  const onPhone = PHONE_ROLES.includes(me.data.role);
  if (onPhone && !phone) return <Navigate to={me.data.role === "foreman" ? "/m/foreman" : "/m"} replace />;
  const Shell = phone ? PhoneShell : AppShell;
  return (
    <Shell me={me.data}>
      <Suspense fallback={<Loading />}>{children(me.data)}</Suspense>
    </Shell>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Signed>{(me) => <Home me={me} />}</Signed>} />
      <Route path="/roster" element={<Signed>{() => <Roster />}</Signed>} />
      <Route path="/roster/:assignmentId" element={<Signed>{() => <AssignmentBuild />}</Signed>} />
      <Route path="/swaps" element={<Signed>{() => <Swaps />}</Signed>} />
      <Route path="/permits" element={<Signed>{(me) => <Permits me={me} />}</Signed>} />
      <Route path="/permits/:permitId" element={<Signed>{(me) => <PermitDetail me={me} />}</Signed>} />
      <Route path="/warnings" element={<Signed>{() => <Warnings />}</Signed>} />
      <Route path="/warnings/:warningId" element={<Signed>{(me) => <WarningRecord me={me} />}</Signed>} />
      <Route path="/district" element={<Signed>{() => <District />}</Signed>} />
      <Route path="/reports" element={<Signed>{() => <Reports />}</Signed>} />
      <Route path="/reports/:kind/:reportId" element={<Signed>{() => <ReportDetail />}</Signed>} />
      <Route path="/inspections" element={<Signed>{() => <Inspections />}</Signed>} />
      <Route path="/actions" element={<Signed>{(me) => <Actions me={me} />}</Signed>} />
      <Route path="/learning" element={<Signed>{() => <Learning />}</Signed>} />
      <Route path="/activities" element={<Signed>{() => <Activities />}</Signed>} />
      <Route path="/activities/:activityId" element={<Signed>{() => <ActivityDetail />}</Signed>} />
      <Route path="/groups" element={<Signed>{() => <Groups />}</Signed>} />
      <Route path="/health" element={<Signed>{() => <Screening />}</Signed>} />
      <Route path="/health/:personId" element={<Signed>{() => <WorkerHealth />}</Signed>} />
      <Route path="/validation" element={<Signed>{() => <Validation />}</Signed>} />
      <Route path="/impact" element={<Signed>{() => <Impact />}</Signed>} />
      <Route path="/governance" element={<Signed>{(me) => <Governance me={me} />}</Signed>} />
      <Route path="/audit" element={<Signed>{() => <Audit />}</Signed>} />
      <Route path="/signals" element={<Signed>{() => <Signals />}</Signed>} />
      <Route path="/admin/people" element={<Signed>{() => <People />}</Signed>} />
      <Route path="/admin/clock" element={<Signed>{() => <SiteClock />}</Signed>} />
      <Route path="/m" element={<Signed phone>{(me) => <WorkerHome me={me} />}</Signed>} />
      <Route path="/m/foreman" element={<Signed phone>{() => <ForemanHome />}</Signed>} />
      <Route path="/m/report" element={<Signed phone>{() => <PhoneReport />}</Signed>} />
      <Route path="/m/cards" element={<Signed phone>{() => <Cards />}</Signed>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
